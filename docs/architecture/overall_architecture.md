# Overall architecture

The extension is organized as a bounded set of layers around the canonical
platform:

1. **Evidence and input layer** — literature candidates, annotations,
   connectome/checkpoint provenance, and calibration targets.
2. **Neural condition layer** — validated data models, burden curves, and
   edge-level perturbation preparation.
3. **Platform adapter layer** — a protocol-compatible action perturbation that
   the platform can call without importing this repository's simulation code.
4. **Execution and artifact layer** — thin scripts that inspect prerequisites,
   delegate execution, and write status/provenance artifacts.
5. **Review and documentation layer** — claim locks, gate reports, manifests,
   and reproducibility records.

```text
reviewed evidence -> condition/annotation -> edge artifact or proxy adapter
                                                |
                                                v
                    canonical platform Perturbation protocol
                                                |
                                                v
                      FlyGym/MuJoCo -> reports/artifacts
```

The platform owns simulation state. This repository owns condition metadata and
its own preparation artifacts. Derived locomotion measurements remain owned by
the platform reports and must not be reimplemented here.
