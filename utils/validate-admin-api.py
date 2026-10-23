#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Validate the checked-in Admin API contract; never download contract inputs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from openapi_spec_validator import OpenAPIV31SpecValidator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[1]
METHODS = {'get', 'put', 'post', 'delete', 'patch', 'head', 'options', 'trace'}
BASE = 'urn:apisix:admin-api'
# These contain instance data, not contract objects or schemas.
DATA = {'example', 'default', 'enum', 'const', 'value'}
MAPS = {'properties', 'patternProperties', '$defs', 'dependentSchemas', 'schemas',
        'paths', 'responses', 'content', 'headers', 'links', 'callbacks', 'pathItems',
        'requestBodies', 'parameters', 'securitySchemes', 'examples'}


def objects(value, path='#', mapping=False):
    """Walk contract objects, keeping arbitrary names and instance data separate."""
    if isinstance(value, dict):
        if not mapping:
            yield path, value
        for key, child in value.items():
            if mapping or (key not in DATA and not key.startswith('x-')):
                if not mapping and key == 'examples' and isinstance(child, list):
                    continue  # JSON Schema examples are instance data.
                yield from objects(child, path + '/' + key.replace('~', '~0').replace('/', '~1'),
                                   not mapping and key in MAPS and isinstance(child, dict))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from objects(child, path + '/' + str(i))


def resolve(document, ref):
    if not isinstance(ref, str) or not ref.startswith('#/'):
        raise ValueError(f'only internal JSON Pointer refs are allowed: {ref!r}')
    result = document
    for token in unquote(ref[2:]).split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        try:
            result = result[int(token)] if isinstance(result, list) else result[token]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f'unresolved ref: {ref}') from exc
    return result


def dereference(document, obj):
    seen = set()
    while isinstance(obj, dict) and '$ref' in obj:
        ref = obj['$ref']
        if ref in seen:
            raise ValueError(f'cyclic Reference Object: {ref}')
        seen.add(ref)
        obj = resolve(document, ref)
    return obj


def absolute_refs(value):
    result = deepcopy(value)
    for _, obj in objects(result):
        for key in ('$ref', '$dynamicRef'):
            if key in obj:
                obj[key] = BASE + obj[key]
    return result


def validate(document, versions):
    """Return actionable errors. Local ref preflight runs before the OAS library."""
    errors = []
    if document.get('openapi') != '3.1.0':
        errors.append('openapi must be 3.1.0')
    version = document.get('info', {}).get('version')
    for source, expected in versions.items():
        if version != expected:
            errors.append(f'info.version {version!r} differs from {source}: {expected!r}')
    for path, obj in objects(document):
        for key in ('$ref', '$dynamicRef'):
            if key in obj:
                try:
                    resolve(document, obj[key])
                except ValueError as exc:
                    errors.append(f'{path}: {exc}')
        if '$id' in obj:
            errors.append(f'{path}: embedded $id changes local ref scope; use document pointers')
    if errors:
        return errors

    schemas = list(document.get('components', {}).get('schemas', {}).items())
    schemas += [(path + '/schema', obj['schema']) for path, obj in objects(document)
                if 'schema' in obj]
    for path, schema in schemas:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            errors.append(f'{path}: invalid JSON Schema: {exc.message}')
    if errors:
        return errors
    errors.extend('OpenAPI: ' + str(e) for e in OpenAPIV31SpecValidator(document).iter_errors())
    if errors:
        return errors
    registry = Registry().with_resource(
        BASE, Resource.from_contents(absolute_refs(document), default_specification=DRAFT202012))

    def check_value(schema, value, location):
        validator = Draft202012Validator(absolute_refs(schema), registry=registry)
        errors.extend(f'{location}: {e.message}' for e in validator.iter_errors(value))

    def check_schema(schema, location):
        for path, obj in objects(schema, location):
            if 'default' in obj:
                check_value(obj, obj['default'], path + '/default')
            if 'examples' in obj:
                for i, example in enumerate(obj['examples']):
                    check_value(obj, example, path + f'/examples/{i}')
            if 'example' in obj:
                check_value(obj, obj['example'], path + '/example')

    # Components plus schemas on parameters, request bodies, response media and headers.
    for name, schema in document.get('components', {}).get('schemas', {}).items():
        check_schema(schema, '#/components/schemas/' + name)
    for path, obj in objects(document):
        if 'schema' not in obj:
            continue
        schema = obj['schema']
        check_schema(schema, path + '/schema')
        if 'example' in obj:
            check_value(schema, obj['example'], path + '/example')
        for name, example in obj.get('examples', {}).items():
            example = dereference(document, example)
            if 'externalValue' in example:
                errors.append(f'{path}/examples/{name}: use a checked-in value, not externalValue')
            elif 'value' in example:
                check_value(schema, example['value'], path + '/examples/' + name)

    ids = set()
    for path, raw_item in document.get('paths', {}).items():
        item = dereference(document, raw_item)
        for method in METHODS & item.keys():
            op = item[method]
            location = f'{method.upper()} {path}'
            if not op.get('responses'):
                errors.append(f'{location}: responses must be non-empty')
            op_id = op.get('operationId')
            if not op_id or op_id in ids:
                errors.append(f'{location}: missing or duplicate operationId {op_id!r}')
            ids.add(op_id)
            params = {}
            for group in (item.get('parameters', []), op.get('parameters', [])):
                for param in group:
                    param = dereference(document, param)
                    params[(param['in'], param['name'])] = param
            declared = {name for (where, name) in params if where == 'path'}
            if declared != set(re.findall(r'{([^{}]+)}', path)):
                errors.append(f'{location}: path parameters do not match template')
            for (where, name), param in params.items():
                if where == 'path' and param.get('required') is not True:
                    errors.append(f'{location}: path parameter {name} must be required')
            for field in ('requestBody', 'responses'):
                entries = op.get('responses', {}).values() if field == 'responses' else [op.get(field)]
                for entry in entries:
                    if entry is None:
                        continue
                    entry = dereference(document, entry)
                    for media, content in entry.get('content', {}).items():
                        if 'schema' not in content:
                            errors.append(f'{location} {field} {media}: missing schema')
    return errors


def repository_versions(root):
    versions = {f'docs/{lang}/latest/config.json': json.loads(
        (root / f'docs/{lang}/latest/config.json').read_text())['version'] for lang in ('en', 'zh')}
    text = (root / 'apisix/core/version.lua').read_text()
    versions['apisix/core/version.lua'] = re.search(r'VERSION\s*=\s*"([^"]+)"', text).group(1)
    return versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', nargs='?', type=Path, default=ROOT / 'docs/en/latest/admin-api.json')
    args = parser.parse_args()
    errors = validate(json.loads(args.spec.read_text()), repository_versions(ROOT))
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Admin API OpenAPI 3.1 contract is valid (refs, operations, schemas, examples, defaults, versions).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
