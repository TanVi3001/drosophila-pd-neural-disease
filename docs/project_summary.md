# Project summary

## Objective

This repository is an evidence-constrained extension around the canonical
`drosophila-pd-flygym` platform. It owns condition metadata, annotation and
provenance checks, edge-level checkpoint preparation, and a platform-compatible
action-level proxy. The platform owns FlyGym/MuJoCo, controller construction,
action application, simulation stepping, locomotion metrics, and runtime
artifacts.

## Pipeline

1. Review literature and provenance.
2. Prepare a healthy computational baseline in the canonical platform.
3. Prepare neural edge artifacts when reviewed inputs exist.
4. Apply an organism-level proxy through the platform `Perturbation` protocol.
5. Keep calibration and holdout workflows claim-locked and provenance-aware.

## Current state

- Platform source contract: `READY` at the local checkout's observed commit.
- Action-level proxy adapter: tested and protocol-compatible.
- Neural edge-checkpoint execution in the platform: `WAITING_PLATFORM_NEURAL_RUNTIME`.
- Historical Gate 12G/13C/14B outputs: retained, but downstream of a superseded
  integration path and therefore requiring current-platform re-execution.
- Literature data: candidate/review status only; no approved calibration target
  is promoted automatically.

## Interpretation boundary

The project provides computational locomotion tooling and proxy experiments. It
does not establish a biological Parkinson mechanism, gene-specific neural
validation, clinical prediction, diagnosis, medication-response claims, or
replacement for wet-lab experiments. See the [current claim lock](claims/current_claim_lock.md)
and [scientific boundaries](architecture/scientific_boundaries.md).
