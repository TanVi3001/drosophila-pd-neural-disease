# Neural and platform execution

This page separates neural-input preparation from platform execution.

## Input audit

Use the repository's provenance checker when a supplied brain source is
available:

```powershell
python scripts/check_neural_inputs.py `
  --brain-root external/fly-brain `
  --output results/neural_input_status.json
```

`READY` means only that the declared inputs passed their audit. It does not
mean that a platform simulation ran.

## Supported action-level proxy

The supported integration is the platform-native perturbation protocol:

```powershell
python scripts/run_platform_proxy_experiment.py `
  --platform-root ..\drosophila-pd-flygym `
  --burden 0.5 `
  --seed 0 `
  --output results/platform_proxy/seed_000
```

The platform owns controller construction, action application, simulation
state, metrics, and artifacts. The extension supplies only the perturbation
object and its operator configuration.

## Neural edge/checkpoint condition

```powershell
python scripts/run_neural_experiment.py `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --config configs/conditions/alpha_synuclein.template.yaml `
  --age-days 20 `
  --annotations annotations/neuron_annotations.csv `
  --output results/alpha_synuclein/day_020/seed_000
```

This prepares and records a checkpoint when inputs are valid, then returns
`WAITING_PLATFORM_NEURAL_RUNTIME` because the current platform does not expose
a checkpoint-consuming neural runner. No rollout, video, or disease metric is
invented in that state.

## Bridge-scale experiment

When a platform-compatible `bridge_scales.json` exists, use the canonical
platform brain-driven entry point through the wrapper:

```powershell
python scripts/run_neural_experiment.py `
  --scales-json ..\drosophila-pd-flygym\data\bridge_scales\pink1_bridge_scales.json `
  --platform-root ..\drosophila-pd-flygym `
  --output results/brain_driven/pink1
```

## New FlyWire-630 LIF condition with explicit MN9 readout

For the public Shiu model, use `run_lif_condition.py` in the separate Brian2
environment. The wrapper validates the completeness inventory, optional
annotation registry, trial denominator, and output checksums before exposing a
metrics artifact:

```powershell
python scripts/run_lif_condition.py `
  --model-root ..\external\Drosophila_brain_model `
  --annotation-file annotations/flywire630_sensory_mn9_public.csv `
  --input-id 720575940624963786 `
  --readout-id 720575940660219265 `
  --seed 0 `
  --trials 1 `
  --duration-s 0.1 `
  --stimulus-rate-hz 150 `
  --output output/sensory_mn9_seed_000
```

Repeat `--input-id` for the complete reviewed set before treating the output
as the public sensory pilot. The result is still computational neural activity
only; it is not a driver-line, causal, disease, or firing-to-behavior claim.

## Boundary

These workflows provide computational locomotion evidence only. They do not
model dopamine loss, alpha-synuclein aggregation, cell death, gene expression,
clinical disease, or treatment efficacy. Missing licenses, annotations,
connectome data, checkpoints, or runtime dependencies must remain explicit
waiting states.
