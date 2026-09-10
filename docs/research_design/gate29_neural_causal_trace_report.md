# Gate29: Neural Causal Trace and Closed-Loop Signal-Path Audit

## 1. Purpose

Gate29 audits the implemented computational execution path before any future
dopamine or disease-layer work. It records which public/runtime signals are
available, the order in which the healthy brain-body runner consumes them, and
whether read-only tracing changes the embodied rollout.

This is an engineering trace of software and physics-model dependencies. It is
not a biological causal inference study.

## 2. Why Gate29 precedes dopamine

The project must first establish what the current healthy runtime actually
exposes to the body. A later neuromodulation gate can only be interpreted
responsibly after the DN boundary, decoder, bridge, controller, actuation and
body-feedback interfaces are explicit.

## 3. Exact runtime loop

At each healthy step in the approved runtime, the audited sequence is:

1. `brain.step()` updates the brain and plasticity state.
2. `brain.get_dn_spikes()` exposes the descending-neuron signal.
3. `decoder.update(...)` updates the rate decoder state.
4. `bridge.compute_drive(...)` reads decoder state and returns a two-element
   `BRAIN_BODY_DRIVE` array.
5. `HybridControllerObservation.from_sim(...)` reads current embodied state.
6. `controller.step(drive, observation)` produces a `LocomotionAction`.
7. `apply_locomotion_action(...)` writes the action to FlyGym/MuJoCo.
8. `simulation.step()` advances the physics state.
9. `recorder.record()` records the post-step observation.

The source file and line references are frozen in
`runtime_execution_path_audit.json`.

## 4. Brain boundary

The verified public brain-to-body boundary is `get_dn_spikes()`. A public full
neuron-state export was not established, so the trace does not inspect private
tensors or infer unexported state.

## 5. DN decoder

`DNRateDecoder` maintains a per-DN sliding state. `update()` mutates the normal
decoder buffers and returns no value; the subsequent `get_rate()` values are
consumed by `BrainBodyBridge.compute_drive()`. The audited window, timestep and
maximum rate are recorded in the signal inventory.

## 6. Brain-body bridge

`BrainBodyBridge.compute_drive(dt=...)` returns a NumPy array with shape `(2,)`.
It is named `BRAIN_BODY_DRIVE` in this gate. It is not called dopamine, a
biological motor command, or a disease signal.

## 7. Closed-loop body feedback

The controller is closed-loop in the computational sense: the current
embodied observation is supplied alongside the bridge drive on every controller
step. The observation includes thorax height, tarsus height, stumbling contact
forces and fly heading. This software feedback path is distinct from any claim
about biological feedback circuitry.

## 8. Engineered CPG/controller

The runtime contains an engineered `HybridTurningController` and an engineered
locomotor CPG implementation. A biologically grounded VNC neural model is not
established by this gate, and the frozen Gate28A boundary is not rewritten.

## 9. Biological VNC limitation

No biological VNC mechanism, gene-specific neural mapping, dopamine pathway or
Parkinson mechanism is validated here. All registered edges explicitly carry
`biological_causality_established: false`.

## 10. Action and physics path

The controller returns `LocomotionAction` with the audited joint-angle and
adhesion fields. The action is written to the simulation before
`simulation.step()`, which produces the next body state. These are
software/physics-model dependencies, not biological causal claims.

## 11. Body-to-assay observation

The body trajectory is later converted through the already-closed Gate28B
adapter from timestamp and thorax XY data to the Riemensperger 2011 open-arena
observation. Gate28B paper-assay equivalence remains false, and Gate29 does not
modify that adapter.

## 12. Signal availability

The committed signal inventory distinguishes public APIs, shapes, timing,
units, export status and semantic confidence. Unavailable signals remain
explicitly unavailable rather than being reconstructed from private state.

## 13. Temporal alignment

Each trace row contains a pre-step time and a post-step time. Step indices and
times are validated as monotonic, with post-step time strictly later than
pre-step time. Actions are captured before physics and body state after
physics. The non-perturbation comparison uses the post-step timestamp and the
frozen tolerances `rtol=0`, `atol=1e-12`; discrete contact arrays require exact
equality.

## 14. Paired non-perturbation test

At most two healthy engineering jobs are authorized: an untraced baseline and
a read-only traced run, both with seed `9201`, 5000 steps, 0.5 seconds of
physical time, the same runtime/checkpoint/controller/physics settings, and no
automatic retry. Raw NPZ files remain outside Git. The result is an engineering
equivalence check, not biological evidence.

## 15. What “causal trace” means here

In Gate29, “causal trace” means that source-code and runtime evidence identify
direct computational dependencies in the executed signal path. It does not
mean that a statistical association or software dependency proves a biological
mechanism.

## 16. What is not established

This gate does not establish biological causality, a VNC neural model, a
dopamine pathway, a Parkinson causal chain, connectome causality, disease
simulation, calibration, fitting, or intervention efficacy.

## 17. Implications for Gate30

Gate30 may introduce a separately specified neuromodulation layer only after
human review of this trace, its signal boundaries and its non-perturbation
result. Gate29 does not authorize dopamine parameters or disease jobs.

## 18. Human review status

The initial signoff template remains
`WAITING_GATE29_HUMAN_REVIEW`. The engineering result cannot self-approve the
gate. The bounded trace runner is statically qualified, but that qualification
does not authorize a real trace execution. The exact next action is
`HUMAN_AUTHORIZE_SINGLE_GATE29_TRACE_ONLY_EXECUTION`, followed by the separate
Gate29 human scientific review, `HUMAN_REVIEW_GATE29_NEURAL_CAUSAL_TRACE`.

## 19. Technical execution outcome

The canonical healthy baseline job completed with seed `9201` and its raw
artifact remains outside Git. The first trace implementation was terminated
after excessive startup overhead before it wrote a trace artifact. That failed
attempt is preserved in the attempt provenance manifest and is not silently
replaced by a retry. The corrected collector is restricted to the audited
runtime script and has passed a deterministic non-GPU scope qualification with
zero non-runtime line events. Therefore the paired non-perturbation comparison
is still `NOT_AVAILABLE_TRACE_JOB_ABORTED`: no real trace artifact exists yet.
Gate29 does not report this as PASS or FAIL, does not execute a trace in this
correction, and does not make any scientific claim from the baseline alone.
The architecture is complete, the trace runner is statically qualified, and
technical execution remains blocked until a human authorizes exactly one
trace-only run at the current commit.

## Claim lock

Allowed wording:

> Gate29 establishes an audited computational execution-path trace from the
> brain/DN interface through the brain-body bridge, closed-loop locomotor
> controller, actuation, physics state, and Gate28B observation layer.

Also allowed:

> The locomotor controller is closed-loop because current embodied state is
> also supplied to `controller.step()`.

Forbidden wording includes: “brain activity biologically causes the locomotor
phenotype”, “VNC mechanism validated”, “dopamine pathway validated”, “Parkinson
causal chain proven”, and “connectome causality proven”.
