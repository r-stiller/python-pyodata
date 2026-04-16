# OData V3 Implementation Progress

This file tracks the current implementation status of OData V3 support in `python-pyodata`.

It is intended as an internal engineering snapshot, not as end-user documentation of fully supported behavior.

## Current Status

The repository now has explicit bootstrap paths for OData V3 metadata plus a narrow but usable runtime slice covering operation invocation, default media-stream reads for `HasStream` entities, named-stream reads for `Edm.Stream` properties, and open-type runtime behavior for dynamic properties on open entity types.

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
- Added V3 unbound function invocation with path-style parameter formatting such as `Func(A=1,B='x')`.
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

## Intentionally Deferred

The following are not implemented yet:

- Generalized request execution changes beyond the current header/payload guardrails and unbound-operation support.
- Spatial runtime behavior.
- Named-stream writes and any broader upload API.
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

V3 service coverage currently passes for:

- V3 Verbose JSON request headers for read and write requests.
- Explicit failure for non-Verbose JSON payloads.
- Unbound function path-style URL generation.
- Deterministic ordering of unbound function parameters.
- Representative primitive literal formatting for unbound function parameters.
- Unbound action `POST` method, request headers, and request body shape.
- Unbound action response handling for return and no-return cases.
- Entity-bound function URL generation and execution.
- Entity-bound action URL generation, `POST` request shape, and execution.
- Rejection of explicit binding-parameter arguments on bound operations.
- Collection-bound function URL generation and deterministic parameter ordering.
- Collection-bound action response handling for no-return cases.
- Default media-stream request construction for V3 media entities.
- Named-stream request construction for V3 `Edm.Stream` properties.
- Raw-content stream reads for default and named streams.
- Explicit failures for unknown or non-stream named-stream access.
- Dynamic-property retention during open-type entity materialization.
- Dynamic-property access through the existing entity-proxy attribute/cache behavior.
- Open-type create/update payload pass-through for undeclared properties.
- Closed-type rejection of undeclared properties.

V3 tests still intentionally remain `xfail` for:

- Spatial primitive resolution.

## Main Files Involved So Far

- [pyodata/client.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/client.py)
- [pyodata/v2/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/model.py)
- [pyodata/v3/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v3/model.py)
- [pyodata/v3/service.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v3/service.py)
- [tests/test_model_v3.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_model_v3.py)
- [tests/test_service_v3.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_service_v3.py)
- [tests/metadata_v3.xml](/C:/Users/r.stiller/dev/python-pyodata/tests/metadata_v3.xml)

## Next Likely Milestones

1. Decide whether the compact V3 scope needs named-stream writes or whether reads remain sufficient.
2. Decide the supported scope for spatial types.
3. Expand V3 runtime support beyond the current operation, stream, and open-type slice only when tests require it.
4. Revisit broader request/query composition only if later fixtures require more than the current narrow bound, unbound, explicit stream, and open-type support.
