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

## 20. Final pre-authorization hardening

The trace-only execution path now runs a mandatory preflight after human
authorization validation and before subprocess launch. The preflight checks
the immutable baseline hashes, baseline brain-source provenance, current brain
source and runtime worktrees, runtime and checkpoint identities, execution
context, GPU telemetry and temperature, trace-only storage capacity, and
attempt-02 existence. Authorization is permission to attempt this preflight;
it cannot bypass a failed integrity check.

The locked baseline metadata records `brain_source_worktree_dirty: true` but
does not contain historical hashes for the execution-critical brain files.
Accordingly, `baseline_source_snapshot.json` records the source commit and
all available metadata while leaving those historical hashes explicitly null.
The preflight must report
`GATE29_TRACE_RESUME_BLOCKED_BASELINE_SOURCE_NOT_REPRODUCIBLE` until exact
content-hash evidence is supplied. No trace is authorized or executed by this
hardening task.

## 21. Baseline brain-source forensic reconstruction

The Gate29 baseline metadata records the brain source commit
`ea00d987edfe65346b36bfa4ce37b628231a5c42` and
`brain_source_worktree_dirty: true`, but it does not record historical
per-file hashes for the five execution-critical source files. The forensic
manifest therefore checks each file independently rather than treating the
commit ID as proof of executed bytes.

The checkpoint `data/plastic_weights.pt` is independently hash-locked by the
baseline metadata and the Gate29 execution lock. The other four files have
matching hashes in the committed Gate11 source audit and in the current source
tree, but that audit is not cryptographically tied to the Gate29 baseline
execution. The source files are also under the ignored `external/` subtree and
no corresponding Git blobs exist at the baseline commit. No historical dirty
path set or unambiguous unreachable object mapping was recovered.

The resulting classification is
`GATE29_BASELINE_BRAIN_SOURCE_RECONSTRUCTION_INCOMPLETE`. The old baseline is
preserved as a real historical engineering execution, but it is not suitable
as the cryptographically controlled counterpart for a new trace-only
non-perturbation comparison. Preflight remains blocked with
`GATE29_TRACE_RESUME_BLOCKED_BASELINE_SOURCE_NOT_REPRODUCIBLE`. This forensic
task did not run GPU, simulation, baseline rerun, or trace attempt 02.

## Claim lock

Allowed wording:

> Gate29 establishes an audited computational execution-path trace from the
> brain/DN interface through the brain-body bridge, closed-loop locomotor
> controller, actuation, physics state, and Gate28B observation layer.

Also allowed:

> The locomotor controller is closed-loop because current embodied state is
> also supplied to `controller.step()`.

## 22. Canonical paired engineering design

The historical seed-9201 baseline remains preserved, but its dirty brain-source
state cannot be reconstructed cryptographically. It is therefore not reused as
the counterpart of a new trace. This gate designs a new pair,
`GATE29_CANONICAL_PAIR_V1`, with engineering seed `9202`. Seed 9202 is not a
scientific replicate, does not replace seed 9201, and is not a Gate31 seed or an
effect-size result.

The pair contains exactly two fresh healthy jobs: an untraced baseline and an
instrumented trace. Both use the same runtime, brain snapshot, checkpoint,
physics, timestep, stimulus, duration, seed, controller, decoder, bridge,
recorder and export profile. The only semantic difference is bounded trace
instrumentation. The two job specifications are compared after removing the
explicit whitelist (`instrumentation_enabled`, `output_directory`, and
`job_label`).

The complete usable `external/fly-brain` source tree is copied once to the
external snapshot root `gate29_canonical_inputs/canonical_pair_v1/brain_source`.
The snapshot is outside Git, every copied file is verified immediately by
SHA-256, and the committed manifest records a deterministic sorted tree
fingerprint. The checkpoint is independently locked to
`d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`.
The original working-tree brain source is no longer an execution input for the
canonical pair.

## 23. Authorization and execution boundary

The committed authorization file starts as
`WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION` with `authorized=false`.
Future authorization must bind the current code head, pair ID, seed, canonical
source-tree fingerprint and runtime commit. It authorizes exactly two jobs,
with no automatic retry; it does not authorize scientific, disease,
calibration, fitting, retuning or dopamine work. The old trace-only plan is
explicitly superseded and its execution path fails with
`GATE29_TRACE_ONLY_PLAN_SUPERSEDED`.

The new output root is
`gate29_technical_outputs/canonical_pair_v1/`, separate from the historical
`neural_causal_trace` output. Design creates only empty baseline, trace and
log directories plus a `NOT_EXECUTED` state marker. No GPU, simulation, trace,
calibration or scientific job is run by this gate. The bounded tracer remains
`AUDITED_RUNTIME_SCRIPT_ONLY`; source-code edge count remains 11 and runtime
verified edge count remains 0.

## 24. Current canonical-pair status

The design artifacts and source snapshot are complete only after the design
command has verified the full copy and fingerprint. The static preflight may
report `GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION` while
the execution state remains `NOT_EXECUTED`. This means the pair is ready for
human authorization, not that a trace result exists. Future comparison is
limited to the new baseline and new trace, with `rtol=0`, `atol=1e-12`, and
exact discrete comparisons. No interpretation of neural causality or biology
is permitted at the design stage.

## 25. Canonical execution-code freeze

The canonical pair execution code is frozen at commit
`513b280d809d1c715c3132aefc3bb23bb2427be5`. This is the exact code identity
that a future human authorization may approve. The historical `a45fa` commit
is retained only as design-era provenance and is not the execution-code
identity.

The freeze binds the healthy pair to seed `9202`, exactly two jobs, the
memory-safe runtime commit, the 11-file brain snapshot tree, the checkpoint
SHA-256, and exact comparison tolerances. Only explicit provenance and human
control metadata may change after the freeze. A source/config/runtime change,
an uncommitted worktree, or a freeze mismatch fails closed as execution-code
drift.

Execution-time snapshot validation reads only the immutable canonical snapshot
and its committed manifest. It does not use the mutable original
`external/fly-brain` checkout. The snapshot is therefore the execution input
(`source_snapshot_execution_input=true`), while the mutable original is not
(`mutable_original_source_execution_input=false`). All 11 files, sizes, hashes
and the sorted tree fingerprint must match.

The engineering pair has no biological holdout role. Its terminology is
`NOT_APPLICABLE_GATE29_ENGINEERING_PAIR`; no external biological evidence was
accessed or evaluated, and no previously exposed study is described as
resealed. Human authorization remains pending, both pair jobs remain
unauthorized, and execution status remains `NOT_EXECUTED`.

Forbidden wording includes: “brain activity biologically causes the locomotor
phenotype”, “VNC mechanism validated”, “dopamine pathway validated”, “Parkinson
causal chain proven”, and “connectome causality proven”.
