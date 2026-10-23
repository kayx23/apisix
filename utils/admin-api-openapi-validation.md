<!--
  Licensed to the Apache Software Foundation (ASF) under one
  or more contributor license agreements.  See the NOTICE file
  distributed with this work for additional information
  regarding copyright ownership.  The ASF licenses this file
  to you under the Apache License, Version 2.0 (the
  "License"); you may not use this file except in compliance
  with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on an
  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
  KIND, either express or implied.  See the License for the
  specific language governing permissions and limitations
  under the License.
-->

# Admin API OpenAPI verification for release/3.17

The self-contained `docs/en/latest/admin-api.json` targets APISIX **3.17.0**.
The reviewed public source baseline is `0e783c9c8e7940d3ecdbe3e983b2ca58583edec9`.
No runtime code, build workflow, fetch step, or dependency on API7 is added.
Existing branding and documentation links are retained.

## Reproduce

From a public release/3.17 checkout with the patch applied:

```sh
python3 -m venv /tmp/apisix-openapi-venv
/tmp/apisix-openapi-venv/bin/pip install lupa==2.8 jsonschema==4.26.0 openapi-spec-validator==0.9.0
/tmp/apisix-openapi-venv/bin/python utils/check-admin-api-openapi.py
python3 -m json.tool docs/en/latest/admin-api.json > /dev/null
git diff --check
```

The checker reads only local files. It evaluates schema tables with Lua 5.1,
without loading APISIX modules. Draft-04 schema dependencies and exclusive bounds
are converted to JSON Schema 2020-12 equivalents for OpenAPI 3.1. The manifest
records SHA-256 hashes of 30 local source files whose dispatch and behavioral
contracts were reviewed. A hash change requires renewed review; hashes alone
are not a semantic proof.

## Validation evidence

- Strict JSON parsing rejects duplicate keys.
- OpenAPI 3.1 document and every component schema validate.
- All references are local and resolve.
- 98 operations have unique, well-formed operation IDs and complete required path parameters.
- 321 example occurrences and 120 default occurrences validate against their schemas.
- 12 core schemas (including ResourceId), 11 write-input variants, the SSL GET variant,
  and all 3 secret-backend schemas match the evaluated release sources.
- Resource handler methods match the resource registrations and unsupported-method lists.
- Deliberate broken-reference, duplicate-operation-ID, missing-path-parameter,
  wrong-version, source-schema-drift, invalid-default, and invalid-example mutations
  were each rejected by the checker.
- Public PEM examples use `t/certs/apisix.crt` and `t/certs/apisix.key`.
  OpenSSL parses the certificate and reports the private key valid. These are test fixtures.
- Python compilation, JSON formatting, and `git diff --check` pass.

The counts above include declaration occurrences; shared schemas are checked once
where declared, and each referenced request/response example is checked against
its resolved schema. The printed reference count also includes source-parity
expansion and is not a count of unique references.

## Source review

| Contract | Local release/3.17 evidence | Specification behavior |
| --- | --- | --- |
| Dispatch and authentication | `apisix/admin/init.lua` | Resource paths; nested credentials; schema/plugin aliases; root HEAD without auth; query/header/cookie key alternatives; viewer GET-only role |
| Resource methods | `apisix/admin/*.lua`, `resource.lua` | Resource-specific unsupported methods; POST generated IDs; item and collection PUT; consumer username matching; credential parent check |
| Schema constraints | `apisix/schema_def.lua` | Exact fields, types, ranges, defaults, dependencies, route exclusivity, TLS limits, stream protocol schema |
| PUT input | `resource.lua` | ID injected from path or required in body; create_time/update_time forbidden, including inline upstream metadata |
| PATCH | `resource.lua`, `apisix/core/table.lua` | Recursive object merge; null deletion; array replacement; complete-result validation; nested sub-path replacement |
| Deletes | `resource.lua`, per-resource delete checkers | force=true bypass; dependency errors; deleted count encoded as string |
| Responses | `apisix/core/etcd.lua`, `v3_adapter.lua`, `init.lua` | PUT 201 for creation, 200 for replacement; default v3 and legacy envelopes; message-based etcd 404 versus error_msg handler errors; 503 failures |
| SSL reads | `resource.lua` | key and keys omitted on GET; write-response variant retains stored fields |
| Queries | `v3_adapter.lua`, `init.lua`, `plugins.lua` | v3 filters and pagination; both numeric page/page_size required; no invented page default; subsystem=http; schema_type=consumer selection |
| Secrets | `apisix/secret/{vault,aws,gcp}.lua`, `admin/secrets.lua` | Backend-dependent payloads and defaults; typed paths; no secret POST |
| Schema lookup | `admin/schema.lua`, `init.lua` | Singular exported core schema names, versus plural resource names for schema validation |
| Batch validation | `admin/config_validate.lua`, `constants.lua` | JSON/YAML; 1.5 MiB limit; resource arrays and numeric versions; duplicate IDs; error collection; no persistence or cross-resource existence checks |
| Standalone | `admin/standalone.lua`, `init.lua` | YAML-provider-only configs; X-Digest required; 202 accepted / 204 unchanged; X-Last-Modified metadata; version retention/removal rules; 500 failures |
| Version and defaults | `apisix/core/version.lua`, `apisix/cli/config.lua` | 3.17.0, default v3 format and Admin port 9180 |

Schema validation does not execute plugin check_schema callbacks, Lua expressions,
certificate installation, reference lookups, etcd operations, or standalone worker
broadcasts. Full APISIX service-backed integration tests were not run in this
environment. These runtime checks remain authoritative; the spec calls them out.
The sub_path wildcard can span slashes, which OpenAPI path-template tools cannot
fully express; clients may need to substitute that path manually.

## Migration provenance

Before editing, both apache/apisix and kayx23/apisix branches and matching open
PRs were checked. Only kayx23's `docs/admin-api-openapi-3.17` checkpoint existed;
it was identical to the release baseline and contained no changes. That branch
was reused. The open-PR check was repeated before publication.

The historical 3.17.0 API7 document at commit
`0b1c689fb12ccc4314cab7661123396f099e0261`, path
`apisix_versioned_docs/version-3.17.0/reference/admin-api.json`, was read once as
migration evidence. It is not a source of truth for the release contracts and
is not fetched by this repository. No 3.19 specification was used.

Independent source review corrected missing route allOf/not rules, name and key
limits, missing TLS dependencies and stream protocol fields, malformed stream
operation IDs, singular schema names, incorrect standalone statuses and digest
requirements, inaccurate SSL/credential/stream examples, and response variants.
