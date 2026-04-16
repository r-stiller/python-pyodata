# OData V2 Implementation Progress

This file tracks the current implementation status of OData V2 support in `python-pyodata`.

It is intended as an internal engineering snapshot of the repository's primary protocol surface.

## Current Status

OData V2 is the default and production-stable protocol implementation in this repository.

It is the only protocol version advertised as supported in [README.md](/C:/Users/r.stiller/dev/python-pyodata/README.md), and the current package, docs, and test suite are centered on V2 behavior.

## Implemented

### Client bootstrap

- Default `pyodata.Client(...)` behavior targets OData V2.
- Sync client creation is implemented.
- Async client creation is implemented.
- Metadata can be supplied directly or fetched from `/$metadata`.

### Metadata/model layer

- EDMX parsing for the supported V2 namespace variants.
- Schema construction for entity types, complex types, enum types, entity sets, associations, and association sets.
- Property metadata parsing including nullability, precision, scale, fixed-length, and SAP-specific attributes.
- Shared metadata parsing for entity-type flags used by the existing V2 runtime surface and by the current V3 layer, including media-entity stream flags and open-type markers as metadata only.
- Navigation property and association resolution.
- Function import metadata parsing for V2 function imports.
- Error-policy based metadata parsing via configurable parser policies.
- Annotation/value-help parsing for supported vocabularies.
- Primitive type registry and literal/JSON conversion helpers.

### Service/runtime layer

- Entity set access and entity lookup by key.
- Query construction with filter/order/select/expand/top/skip and related query options.
- Entity create, update, and delete requests.
- Function import invocation with V2 request semantics.
- Media-entity `$value` access on entity and navigation-based entity proxies.
- URL/path/body extraction helpers for external HTTP execution.
- Batch requests and changesets.
- Response parsing for entities, collections, and primitive results.

### Compatibility surface

- User-facing documentation under [docs/usage](/C:/Users/r.stiller/dev/python-pyodata/docs/usage).
- Vendor-specific helpers under [pyodata/vendor](/C:/Users/r.stiller/dev/python-pyodata/pyodata/vendor).
- CI compatibility across Python `3.9` through `3.14`.

## Main Coverage Areas

The current repository has direct V2 coverage for:

- Model parsing in [tests/test_model_v2.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_model_v2.py)
- Type serialization and null handling in [tests/test_model_v2_EdmStructTypeSerializer.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_model_v2_EdmStructTypeSerializer.py)
- Variable declaration behavior in [tests/test_model_v2_VariableDeclaration.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_model_v2_VariableDeclaration.py)
- Service/runtime behavior in [tests/test_service_v2.py](/C:/Users/r.stiller/dev/python-pyodata/tests/test_service_v2.py)
- Networking-library integration coverage under [tests/integration/networking_libraries](/C:/Users/r.stiller/dev/python-pyodata/tests/integration/networking_libraries)

## Known Scope Notes

These are not necessarily defects, but they define the practical scope of the current V2 implementation:

- The compatibility contract is driven by the existing V2 public API and test suite.
- Vendor-specific behavior should stay isolated in [pyodata/vendor](/C:/Users/r.stiller/dev/python-pyodata/pyodata/vendor).
- Metadata handling includes SAP-oriented extensions that are already part of the effective V2 surface.
- Shared model objects now also carry some metadata bits used by the V3 layer, but V2 runtime behavior remains the stable strict baseline.
- Changes in [pyodata/v2/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/model.py) and [pyodata/v2/service.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/service.py) carry broad regression risk and should stay narrow.

## Main Files

- [pyodata/client.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/client.py)
- [pyodata/v2/model.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/model.py)
- [pyodata/v2/service.py](/C:/Users/r.stiller/dev/python-pyodata/pyodata/v2/service.py)
- [pyodata/vendor](/C:/Users/r.stiller/dev/python-pyodata/pyodata/vendor)
- [docs/usage](/C:/Users/r.stiller/dev/python-pyodata/docs/usage)

## Maintenance Guidance

When changing V2 behavior:

1. Treat V2 as the stable baseline.
2. Prefer behavior-preserving fixes over refactors.
3. Add or update tests for any observable change.
4. Update user-facing docs and `CHANGELOG.md` when the public V2 contract changes.
