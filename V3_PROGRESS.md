# OData V3 Implementation Progress

This file tracks the current implementation status of OData V3 support in `python-pyodata`.

It is intended as an internal engineering snapshot, not as end-user documentation of fully supported behavior.

## Current Status

The repository now has an explicit first OData V3 milestone: opt-in bootstrap via `odata_version=3`, Verbose-JSON-only request and response handling, a coherent tested runtime slice, supported batch handling for the covered request and response shapes, and networking-library integration coverage across `requests`, `httpx` sync, `httpx` async, and `aiohttp`.

## Implemented

### Session 1 baseline

- Added compact V3 metadata fixtures.
- Added focused V3 test coverage.

### Session 2 bootstrap support

- Added `Client.ODATA_VERSION_3`.
- Added `pyodata.v3.model`.
- Added `pyodata.v3.service`.
- Enabled direct sync and async client bootstrap for V3.

### Session 3 request/header policy

- Added V3 request policy with `MaxDataServiceVersion: 3.0`.
- Restricted current V3 JSON handling to Verbose JSON.
- Added explicit failure for non-Verbose JSON payloads.

### Session 4 metadata parsing essentials

- Added V3-specific metadata builder behavior in `pyodata.v3.model`.
- Added alias collection from `Schema Alias="..."`.
- Added alias collection from `edm:Using Namespace="..." Alias="..."`.
- Added alias-aware type resolution for V3 metadata parsing.
- Extended parsed `FunctionImport` metadata to expose:
  - `is_bindable`
  - `is_side_effecting`
  - `is_composable`
  - `entity_set_path`
  - binding-parameter identification
- Added V3 `ReturnType` parsing support for the forms covered by current V3 tests.

### Session 5 unbound operation invocation

- Added a V3-specific unbound operation container in `pyodata.v3.service`.
- Added V3 unbound function invocation with query-string parameter formatting such as `Func?A=1&B='x'`, matching the public V3 reference service.
- Kept parameter ordering deterministic by following metadata declaration order.
- Reused existing parameter literal conversion for V3 function URL arguments.
- Added V3 unbound action invocation with `POST` semantics.
- Added V3 action request bodies using existing parameter JSON conversion.
- Preserved current return/no-return response handling for unbound V3 operations under the Verbose JSON contract.
- Kept V2 function-import request semantics unchanged by isolating the V3 runtime behavior in `pyodata.v3.service`.

### Session 6 bound operation invocation

- Added V3-specific bound operation containers on supported entity and entity-set proxy surfaces.
- Added entity-bound operation access from V3 entity contexts.
- Added collection-bound operation access from V3 entity-set contexts for the fixture shapes covered by current tests.
- Kept the binding parameter implicit and rejected explicit caller attempts to supply it.
- Added V3 bound function invocation with binding-path URL shapes such as `Documents(1)/GetPeerDocument(Mode='related')`.
- Added V3 bound action invocation with `POST` semantics and qualified action segments such as `Documents(1)/V3DemoContainer.Approve`.
- Reused the current Verbose JSON response handling for bound operations, including return and no-return cases covered by the tests.
- Kept the V2 runtime surface unchanged by isolating the bound-operation work in `pyodata.v3.service` and using only a narrow shared metadata addition for container-name tracking.

### Session 7 media entities and named streams

- Exposed `HasStream` on parsed V3 entity types.
- Exposed `Edm.Stream` properties through the shared type system in a form usable by V3 runtime code.
- Added explicit V3 `media_stream()` access for default media streams on `HasStream` entities.
- Added explicit V3 `named_stream(name)` access for named streams declared as `Edm.Stream`.
- Kept stream responses as raw HTTP content rather than routing them through the Verbose JSON payload handler.
- Added explicit failures when callers request unknown properties or properties not declared as `Edm.Stream`.
- Kept V2 runtime behavior unchanged by isolating the stream access surface in `pyodata.v3.service` and limiting shared model changes to the metadata/type information required by the V3 tests.

### Session 8 open types

- Exposed `OpenType="true"` on parsed V3 entity types as `EntityType.is_open_type`.
- Kept the shared model addition narrow so the metadata bit is available to V3 without weakening V2 runtime behavior.
- Added V3 entity materialization support that retains undeclared properties from Verbose JSON payloads when the entity type is open.
- Kept dynamic properties on the existing proxy surface by caching them and exposing them through normal attribute access.
- Added V3 create/update support that allows undeclared properties only for open entity types.
- Preserved strict undeclared-property failures for closed entity types.
- Kept V2 behavior unchanged by isolating the read/write relaxation in `pyodata.v3.service`.

### Session 9 primitive and spatial coverage

- Added V3-only primitive registration for the currently tested spatial primitive family, including `Edm.GeographyPoint` and `Edm.GeometryPoint`.
- Kept the implementation narrow by registering these types from `pyodata.v3.model` onto the shared type registry rather than redesigning the common type system.
- Added opaque JSON-compatible spatial type traits that accept and return stable Python mappings for Verbose JSON payloads.
- Added V3 entity materialization support for the tested spatial property payloads without introducing custom Python geometry classes.
- Added V3 create/update serialization support that round-trips the tested spatial mappings back into JSON request bodies.
- Added explicit failures for unsupported spatial URL literal usage rather than guessing a V3 URI literal format.
- Added explicit failures for unsupported spatial operation-parameter usage rather than guessing V3 function/action parameter encoding.
- Kept V2 runtime behavior unchanged by isolating the new primitive/runtime behavior in the V3 facade layer.

### Session 10 milestone wrap-up

- Added focused V3 batch coverage for the supported read and action request/response shapes under the current Verbose JSON contract.
- Confirmed and documented V3 bootstrap plus representative request/header behavior across `requests`, `httpx` sync, `httpx` async, and `aiohttp`.
- Added a narrow shared async response-normalization path so both async-context-manager clients and awaitable-response clients work through the same client/bootstrap code paths.
- Updated `README.md`, `docs/usage/`, `docs/protocol_references.rst`, and `CHANGELOG.md` so the repository’s documented protocol support matches the actual V3 milestone now in tree.

### Session 11 reference-service alignment

- Added captured fixtures for the public `services.odata.org` V3 reference services under `tests/fixtures/reference_services_v3/`.
- Added optional live smoke tests gated by `PYODATA_RUN_REFERENCE_SERVICE_LIVE=1` so default CI remains offline.
- Expanded V3 metadata coverage to parse the public `OData.svc`, read-write `OData.svc`, and `Northwind` metadata snapshots.
- Expanded V3 service coverage to exercise public reference-service entity reads, collection queries, named-stream reads, spatial payloads, and unbound function invocation.
- Updated shared `Edm.DateTime` JSON parsing to accept the ISO timestamp payload shape returned by the public V3 reference service.
- Added default HTTP-method inference for function imports whose metadata omits `m:HttpMethod`, covering the current public read-write V3 metadata.

## Intentionally Deferred

The following are not implemented yet:

- Generalized request execution changes beyond the current header/payload guardrails, the supported batch slice, and the current operation/runtime support.
- Spatial URL/key literal support.
- Spatial query and filter syntax.
- Spatial function/action parameter encoding.
- Named-stream writes and any broader upload API.
- JSON Light payload support.
- Atom payload support for V3 runtime requests and responses.
- Broad parser redesign across all protocol versions.

## Test Status Snapshot

V3 model coverage currently passes for:

- V3 EDM namespace acceptance.
- Alias declaration extraction from `Schema Alias` and `edm:Using`.
- Alias-based property type resolution.
- V3 function import metadata flags.
- V3 return type parsing used by later runtime work.
- Binding-parameter metadata exposure for bound operations.
- `HasStream` exposure on V3 entity types.
- `OpenType` exposure on V3 entity types.
- `Edm.Stream` property resolution for the fixture metadata.
- V3-only spatial primitive registration and lookup for the current fixture types.
- Metadata parsing of entity properties declared as `Edm.GeographyPoint` and `Edm.GeometryPoint`.

V3 service coverage currently passes for:

- V3 Verbose JSON request headers for read and write requests.
- Explicit failure for non-Verbose JSON payloads.
- Unbound function query-string URL generation aligned with the public V3 reference service.
- Deterministic ordering of unbound function parameters.
- Representative primitive literal formatting for unbound function parameters.
- Unbound action `POST` method, request headers, and request body shape.
- Unbound action response handling for return and no-return cases.
- Entity-bound function URL generation and execution.
- Entity-bound action URL generation, `POST` request shape, and execution.
- Rejection of explicit binding-parameter arguments on bound operations.
- Collection-bound function URL generation and deterministic parameter ordering.
- Collection-bound action response handling for no-return cases.
- Batch request execution for the supported Verbose JSON read and action response shapes.
- Default media-stream request construction for V3 media entities.
- Named-stream request construction for V3 `Edm.Stream` properties.
- Raw-content stream reads for default and named streams.
- Explicit failures for unknown or non-stream named-stream access.
- Dynamic-property retention during open-type entity materialization.
- Dynamic-property access through the existing entity-proxy attribute/cache behavior.
- Open-type create/update payload pass-through for undeclared properties.
- Closed-type rejection of undeclared properties.
- Spatial property materialization from Verbose JSON payloads.
- Spatial property round-trip in create/update request bodies using opaque mapping values.
- Explicit failure for unsupported spatial literal/filter usage.
- Explicit failure for unsupported spatial operation-parameter usage.

V3 networking-library integration coverage currently passes for:

- Sync bootstrap with `requests`.
- Sync bootstrap with `httpx`.
- Async bootstrap with `httpx.AsyncClient`.
- Async bootstrap with `aiohttp.ClientSession`.
- Representative V3 entity reads with Verbose JSON headers for all four supported client integrations.
- Captured-fixture regression coverage for the public `services.odata.org` V3 `OData.svc` and `Northwind` services.

## Main Files Involved So Far

- [pyodata/client.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/client.py)
- [pyodata/v2/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/model.py)
- [pyodata/v3/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v3/model.py)
- [pyodata/v3/service.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v3/service.py)
- [tests/integration/networking_libraries](/C:/Users/r.stiller/dev/python-pyodata/tests/integration/networking_libraries)
- [tests/test_model_v3.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_model_v3.py)
- [tests/test_service_v3.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_service_v3.py)
- [tests/metadata_v3.xml](/C:/Users/r.stiller/dev/python-pyodata/tests/metadata_v3.xml)

## Next Likely Milestones

1. Decide whether the first V3 milestone should grow beyond Verbose JSON into JSON Light, or whether that remains explicitly unsupported.
2. Decide whether the compact V3 scope needs named-stream writes or whether reads remain sufficient.
3. Decide whether spatial support should stay payload-only or expand into key literals, filters, and operation parameters.
4. Expand V3 runtime support beyond the current operation, batch, stream, open-type, and payload-only spatial slice only when tests require it.
