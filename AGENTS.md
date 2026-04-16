# AGENTS.md

## Purpose

This repository should be approached as a Python OData V2 client library with a stable public surface, a `pixi`-first local workflow, and a CI-defined compatibility contract. Optimize for small, behavior-preserving changes unless the task explicitly requires a public behavior change.

## Canonical Repo Map

- Runtime package code lives in `pyodata/`.
- Core client entrypoint is `pyodata/client.py`.
- Metadata parsing, schema construction, and type conversion live in `pyodata/v2/model.py`.
- Request building, entity operations, batching, and fluent query behavior live in `pyodata/v2/service.py`.
- Vendor-specific helpers live in `pyodata/vendor/`.
- Tests live in `tests/`, including sync and async networking integrations under `tests/integration/networking_libraries/`.
- User-facing docs live in `docs/usage/`.
- Internal protocol status snapshots live in `V2_PROGRESS.md` and `V3_PROGRESS.md`; use them as orientation for current implementation state, not as a replacement for tests or the public compatibility contract.
- The effective package and CI contract is defined by `setup.py`, `README.md`, `Makefile`, and `.github/workflows/`.

## Source Of Truth And Tooling

- Treat the existing package layout and CI matrix as authoritative.
- Use `pixi` as the default local development environment.
- The main local dev environment is `pyodata-dev` from `pyproject.toml`.
- Preserve compatibility with the GitHub Actions test matrix, which covers Python `3.9` through `3.14` and multiple `lxml` versions.
- Prefer the expectations encoded in `setup.py`, `README.md`, `Makefile`, and CI over local workspace defaults when compatibility requirements disagree.
- Treat `pixi` as the main way to enter a working environment, but treat CI and the published package layout as the final compatibility contract.
- Do not treat `src/python_pyodata/` as the normal implementation target. Only touch it when deliberately changing packaging or workspace wiring.

## Edit Rules By Subsystem

### `pyodata/client.py`

- Keep sync and async client creation behavior aligned.
- Preserve URL normalization, metadata fetch semantics, MIME checks, and error behavior.
- Be careful with deprecated namespace handling; existing warnings are part of the compatibility surface.

### `pyodata/v2/model.py`

- Keep changes narrow. This file is large and central to metadata parsing behavior.
- Preserve namespace detection, schema building, type lookup, serialization, null handling, and error-policy behavior unless the task explicitly changes them.
- Assume small parsing changes can affect many tests; validate accordingly.

### `pyodata/v2/service.py`

- Preserve fluent API behavior for entities, query options, filters, function imports, batching, and changesets.
- Be careful with URL/path encoding, query parameter ordering, JSON payload formatting, and HTTP status handling.
- Keep sync and async execution behavior consistent where both paths exist.

### `pyodata/v3/model.py`

- Keep V3 changes additive and narrow; this layer currently extends the shared V2 model machinery rather than replacing it.
- Preserve alias handling, V3 namespace acceptance, the current stream-related metadata exposure (`HasStream` and `Edm.Stream`), and the current `FunctionImport` metadata shape used by the V3 service layer, including bindability flags, binding-parameter identification, entity-set-path data, and container-name metadata used for bound actions.
- Avoid speculative parser expansion beyond the behaviors covered by the V3 fixtures and tests.

### `pyodata/v3/service.py`

- Prefer V3-specific request/container classes over broad edits to `pyodata/v2/service.py`.
- Keep V2 `service.functions.*` behavior unchanged; V3 differences should stay isolated here.
- Current V3 runtime scope includes explicit header policy, Verbose-JSON-only parsing, unbound operation invocation, the current bound operation slice from entity and entity-set contexts, and explicit stream access for media entities and named streams.
- Preserve the current V3 distinction between unbound and bound operations, including implicit binding parameters, path-style bound functions, and qualified bound-action segments.
- Keep default media-stream and named-stream access on explicit V3 proxy methods; do not broaden V2 proxy semantics to match.
- Open-type runtime behavior, spatial runtime behavior, and broader stream write/upload surfaces remain deferred unless the task explicitly takes them on.

### `pyodata/vendor/`

- Keep vendor-specific behavior isolated here.
- Do not move generic library behavior into vendor helpers.

## Change Strategy

- Maintain OData V2 behavior and backward-compatible public APIs unless the task explicitly requires a breaking change.
- Prefer narrowly scoped edits. `model.py` and `service.py` have broad behavioral blast radius.
- Add or update tests for every behavior change.
- Update `docs/usage/` and `CHANGELOG.md` when public behavior changes.
- Avoid opportunistic refactors in the same patch unless they are required to make the target change safe.

## Validation

Use `pixi` for local validation by default:

```bash
pixi run -e pyodata-dev python -m pytest --cov-report term --cov=pyodata
pixi run -e pyodata-dev pylint --rcfile=.pylintrc --output-format=parseable --reports=no pyodata
pixi run -e pyodata-dev flake8 --config=.flake8 pyodata
pixi run -e pyodata-dev make -C docs html
```

Notes:

- `pixi shell -e pyodata-dev` is the preferred interactive setup when working locally.
- CI still uses the legacy pip-and-`make` flow. Keep changes compatible with those commands even if you validate through `pixi`.
- If `make` is inconvenient on Windows, run the underlying commands inside the `pixi` environment instead.
- If the task does not affect docs, doc builds are optional.
- If local tooling is unavailable, still keep the change aligned with the commands and files above.

## Test Selection Guide

- Metadata parsing, schema construction, or type conversion changes: run `tests/test_model_v2*.py`.
- Service, request construction, entity CRUD, filters, or batching changes: run `tests/test_service_v2.py`.
- V3 metadata/model changes: run `tests/test_model_v3.py`.
- V3 service/runtime changes: run `tests/test_service_v3.py` and the most relevant V2 regression coverage, usually `tests/test_service_v2.py`.
- Client creation, metadata fetch, or sync/async session compatibility changes: run `tests/integration/networking_libraries/`.
- Vendor-specific changes: run the corresponding vendor tests such as `tests/test_vendor_sap.py` or `tests/test_vendor_microsoft.py`.

## Known Pitfalls

- The repo contains both legacy and newer packaging metadata; follow CI and the published package behavior when they disagree.
- The default local `pixi` environment currently resolves to a narrower/newer Python than the full CI compatibility range.
- A change that looks local inside `model.py` or `service.py` can easily affect request serialization, parsing defaults, or compatibility across multiple HTTP client integrations.
