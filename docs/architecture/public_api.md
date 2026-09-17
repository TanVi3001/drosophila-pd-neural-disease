# Public API

The package root exposes:

- `__version__`;
- `DiseaseCondition`, `DiseaseProfile`, and `NeuralParameters`;
- `perturb_edges` and `seeded_noise`;
- `apply_proxy_burden_to_action` and
  `apply_proxy_operator_to_locomotion_action`;
- `ProxyBurdenPerturbation`, which implements the canonical platform
  `Perturbation` protocol by duck typing;
- `PlatformContract`, `inspect_platform`, and `default_platform_root`.

The platform package itself is not imported at package import time. This keeps
the extension's data and contract tests usable without a FlyGym installation.
Platform imports occur only in the thin launcher
`scripts/run_platform_proxy_experiment.py`.

The `src/drosophila_pd_neural` modules and their `__all__` declarations are the
authoritative public surface. Changes to those symbols require tests and a
documentation note.
