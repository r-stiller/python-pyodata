# OData V3 Implementation Progress

This file tracks the current implementation status of OData V3 support in `python-pyodata`.

It is intended as an internal engineering snapshot, not as end-user documentation of fully supported behavior.

## Current Status

The repository now has explicit bootstrap paths for OData V3 metadata and service wiring, but V3 runtime behavior is still incomplete.

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

## Intentionally Deferred

The following are not implemented yet:

- Unbound function URL semantics.
- Bound function invocation.
- Bound action invocation.
- Request execution changes beyond the current header/payload guardrails.
- Open type runtime behavior.
- Named stream runtime behavior.
- Spatial runtime behavior.
- Broad parser redesign across all protocol versions.

## Test Status Snapshot

V3 model coverage currently passes for:

- V3 EDM namespace acceptance.
- Alias declaration extraction from `Schema Alias` and `edm:Using`.
- Alias-based property type resolution.
- V3 function import metadata flags.
- V3 return type parsing used by later runtime work.
- Binding-parameter metadata exposure for bound operations.

V3 tests still intentionally remain `xfail` for:

- Open type and stream metadata exposure.
- Spatial primitive resolution.
- Bound and unbound runtime operation behavior in the service layer.
- Named stream service APIs.
- Open type CRUD behavior.

## Main Files Involved So Far

- [pyodata/client.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/client.py)
- [pyodata/v2/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/model.py)
- [pyodata/v3/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v3/model.py)
- [pyodata/v3/service.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v3/service.py)
- [tests/test_model_v3.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_model_v3.py)
- [tests/test_service_v3.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_service_v3.py)
- [tests/metadata_v3.xml](/C:/Users/r.stiller/dev/python-pyodata/tests/metadata_v3.xml)

## Next Likely Milestones

1. Define V3 unbound function URL generation.
2. Add bound function and action model-to-service integration.
3. Add named stream surface and request behavior.
4. Decide the supported scope for open types and spatial types.
