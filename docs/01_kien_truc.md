# Repository architecture

`drosophila-pd-flygym` is the canonical simulation platform. It owns
FlyGym/MuJoCo versions, world and fly construction, controllers, action
application, simulation stepping, locomotion metrics, runtime artifacts, and
platform documentation.

This repository is an additive research extension:

```text
literature / annotations / provenance
                |
                v
condition and edge-level preparation ----> checkpoint artifact
                |
                v
       platform Perturbation protocol
                |
                v
FlyGym/MuJoCo simulation ----> platform-owned reports and metrics
```

The action-level proxy path is supported today. A neural edge checkpoint is a
separate preparation artifact; the current platform has no compatible runner
that consumes it, so that workflow stops at
`WAITING_PLATFORM_NEURAL_RUNTIME`.

Do not copy platform source, invent platform APIs, or treat a preparation
artifact as a locomotion result. See the [platform contract](architecture/platform_contract.md).
