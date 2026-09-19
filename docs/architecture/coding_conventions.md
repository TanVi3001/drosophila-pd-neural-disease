# Coding conventions

- Target Python 3.12 and use the `src/` package layout from `pyproject.toml`.
- Use `pathlib.Path`, explicit UTF-8 encoding, structured JSON/YAML parsing,
  deterministic ordering, and finite-number validation at boundaries.
- Keep scripts thin; reusable behavior belongs in
  `src/drosophila_pd_neural/`.
- Consume the platform's documented APIs and protocols. Do not copy platform
  implementations or rely on private symbols when a public contract exists.
- Preserve input immutability for action and edge transformations.
- Record status, source paths, commit/checksum, and scientific scope in output
  manifests.
- Missing data, missing runtime, and unsupported capability must be explicit;
  never fill them with zeros, mocks, or fabricated rollouts.
- Add tests for public behavior, serialization, failure states, and platform
  compatibility.

Required baseline:

```powershell
python -m compileall -q src scripts tests
python -m pytest -q -rs -p no:cacheprovider
git diff --check
```
