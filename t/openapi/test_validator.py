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

"""Mutation tests exercise validator failures independently of the large spec."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE = importlib.util.spec_from_file_location('validator', ROOT / 'utils/validate-admin-api.py')
validator = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(validator)


def fixture():
    return {
        'openapi': '3.1.0', 'info': {'title': 'Test', 'version': '1.0'},
        'paths': {'/things/{id}': {
            'parameters': [{'name': 'id', 'in': 'path', 'required': True,
                            'schema': {'type': 'string'}}],
            'put': {'operationId': 'putThing',
                    'requestBody': {'content': {'application/json': {
                        'schema': {'$ref': '#/components/schemas/Thing'},
                        'example': {'count': 1}}}},
                    'responses': {'200': {'description': 'OK', 'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/Thing'},
                                             'examples': {'ok': {'value': {'count': 2}}}}}}}}}},
        'components': {'schemas': {'Thing': {'type': 'object', 'required': ['count'],
                        'properties': {'count': {'type': 'integer', 'minimum': 1, 'default': 1}},
                        'additionalProperties': False}}}}


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.doc = fixture()
        self.op = self.doc['paths']['/things/{id}']['put']
        self.schema = self.doc['components']['schemas']['Thing']
        self.request = self.op['requestBody']['content']['application/json']
        self.response = self.op['responses']['200']['content']['application/json']

    def errors(self):
        return validator.validate(self.doc, {'test version': '1.0'})

    def assert_invalid(self, text):
        self.assertIn(text, '\n'.join(self.errors()))

    def test_valid(self):
        self.assertEqual([], self.errors())

    def test_openapi_version(self):
        self.doc['openapi'] = '3.0.3'
        self.assert_invalid('openapi must be 3.1.0')

    def test_document_version(self):
        self.doc['info']['version'] = 'old'
        self.assert_invalid('differs from test version')

    def test_openapi_structure(self):
        del self.doc['info']['title']
        self.assert_invalid('OpenAPI:')

    def test_broken_ref(self):
        self.request['schema']['$ref'] = '#/components/schemas/Missing'
        self.assert_invalid('unresolved ref')

    def test_no_remote_refs(self):
        self.request['schema']['$ref'] = 'https://invalid.example/never-fetch.json'
        self.assert_invalid('only internal')

    def test_escaped_pointer(self):
        self.schema['properties']['a/b~c'] = {'type': 'integer'}
        self.request['schema'] = {'$ref': '#/components/schemas/Thing/properties/a~1b~0c'}
        self.request['example'] = 1
        self.assertEqual([], self.errors())

    def test_duplicate_operation_id(self):
        self.doc['paths']['/things/{id}']['get'] = deepcopy(self.op)
        self.assert_invalid('not unique')

    def test_missing_operation_id(self):
        del self.op['operationId']
        self.assert_invalid('missing or duplicate operationId')

    def test_missing_path_parameter(self):
        self.doc['paths']['/things/{id}']['parameters'] = []
        self.assertTrue(self.errors())

    def test_extra_path_parameter(self):
        self.op['parameters'] = [{'in': 'path', 'name': 'extra', 'required': True,
                                  'schema': {'type': 'string'}}]
        self.assertTrue(self.errors())

    def test_optional_path_parameter(self):
        self.doc['paths']['/things/{id}']['parameters'][0]['required'] = False
        self.assertTrue(self.errors())

    def test_operation_overrides_path_parameter(self):
        self.op['parameters'] = [deepcopy(self.doc['paths']['/things/{id}']['parameters'][0])]
        self.assertEqual([], self.errors())

    def test_invalid_schema(self):
        self.schema['properties']['count']['type'] = 'nonsense'
        self.assert_invalid('invalid JSON Schema')

    def test_invalid_default(self):
        self.schema['properties']['count']['default'] = 0
        self.assert_invalid('less than the minimum')

    def test_invalid_schema_example(self):
        self.schema['examples'] = [{'count': 0}]
        self.assert_invalid('/examples/0')

    def test_invalid_request_example(self):
        self.request['example'] = {'count': 'bad'}
        self.assert_invalid('/example')

    def test_invalid_response_example(self):
        self.response['examples']['ok']['value'] = {}
        self.assert_invalid('required property')

    def test_referenced_example(self):
        self.doc['components']['examples'] = {'Bad': {'value': {'count': 0}}}
        self.response['examples']['ok'] = {'$ref': '#/components/examples/Bad'}
        self.assert_invalid('less than the minimum')

    def test_missing_request_schema(self):
        del self.request['schema']
        self.assert_invalid('requestBody application/json: missing schema')

    def test_missing_response_schema(self):
        del self.response['schema']
        self.assert_invalid('responses application/json: missing schema')

    def test_bodyless_response_allowed(self):
        self.op['responses'] = {'204': {'description': 'No content'}}
        self.assertEqual([], self.errors())

    def test_arbitrary_example_data(self):
        self.schema['additionalProperties'] = True
        self.request['example']['$ref'] = 'this is user data, not a reference'
        self.assertEqual([], self.errors())

    def test_keyword_property_names(self):
        self.schema['properties'].update({
            'schema': {'type': 'string'},
            'default': {'type': 'integer', 'default': 0},
            'examples': {'type': 'string'},
            'x-value': {'type': 'integer'}})
        self.assertEqual([], self.errors())
        self.schema['properties']['x-value']['default'] = 'bad'
        self.assertTrue(self.errors())

    def test_remote_example_ref_is_rejected(self):
        self.response['examples']['ok'] = {'$ref': 'https://invalid.example/example'}
        self.assert_invalid('only internal')

    def test_missing_responses(self):
        del self.op['responses']
        self.assert_invalid('responses must be non-empty')

    def test_json_schema_31_null(self):
        self.schema['properties']['count']['type'] = ['integer', 'null']
        self.request['example']['count'] = None
        self.assertEqual([], self.errors())

    def test_repository_versions(self):
        versions = validator.repository_versions(ROOT)
        self.assertEqual(3, len(versions))
        self.assertEqual(1, len(set(versions.values())))

    def test_master_cluster_ids(self):
        doc = json.loads((ROOT / 'docs/en/latest/admin-api.json').read_text())
        upstream = doc['components']['schemas']['Upstream']
        cluster = upstream['properties']['discovery_args']['properties']['cluster_ids']
        check = validator.Draft202012Validator(cluster)
        self.assertTrue(check.is_valid(['release', 'staging']))
        for invalid in ([], ['release', 'release'], [1], 'release'):
            with self.subTest(invalid=invalid):
                self.assertFalse(check.is_valid(invalid))


    def test_cluster_ids_in_all_upstream_forms(self):
        doc = json.loads((ROOT / 'docs/en/latest/admin-api.json').read_text())
        schemas = doc['components']['schemas']
        for name in ('Upstream', 'ConfigValidationUpstream', 'UpstreamPatch',
                     'RoutePatch', 'ServicePatch'):
            with self.subTest(schema=name):
                schema = schemas[name]
                if name in ('RoutePatch', 'ServicePatch'):
                    schema = schema['properties']['upstream']
                cluster = schema['properties']['discovery_args']['properties']['cluster_ids']
                check = validator.Draft202012Validator(cluster)
                self.assertTrue(check.is_valid(['release']))
                self.assertFalse(check.is_valid([]))
                self.assertFalse(check.is_valid(['release', 'release']))
                self.assertEqual('Patch' in name, check.is_valid(None))

    def test_stream_route_get_envelope(self):
        doc = json.loads((ROOT / 'docs/en/latest/admin-api.json').read_text())
        media = doc['paths']['/apisix/admin/stream_routes/{id}']['get'][
            'responses']['200']['content']['application/json']
        self.assertEqual({'$ref': '#/components/schemas/StreamRouteEnvelope'}, media['schema'])
        self.assertEqual('/apisix/stream_routes/1', media['examples']['1']['value']['key'])


if __name__ == '__main__':
    unittest.main()
