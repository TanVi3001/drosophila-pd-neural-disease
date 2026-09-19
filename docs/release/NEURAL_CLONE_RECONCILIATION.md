# Neural Clone Reconciliation

This repository is the canonical neural repository for the workspace.

## Source records

- Canonical baseline: `d5a0c76a970de85dea7e0cacdc00ef5ab51f15d0`.
- Preserved user gate updates: `f767107`.
- Source-only neural release snapshot: `cd176f9fa92c736d6189d4316ef9b4a8a5cf6706`.
- Integration commit: `b71b7f9c070349d2631d69afc43b058158af1255`.
- Final compatibility and evidence reconciliation: `69c614a`.

## Policy

The canonical `main` evidence tree remains authoritative. New source-only
capabilities were imported only when they did not replace existing gate
artifacts, reproducibility locks, or canonical claim documents. Large PDFs,
raw experiment outputs, external connectome repositories, and frozen platform
worktrees remain external inputs and are not duplicated in this repository.

Gate24 remains explicitly blocked until the required model freeze, checkpoint,
and neural transform inputs are present. No biological Parkinson validation
claim is made by this repository.

The source-only clone is retained as a historical release snapshot and is not
used as a second root-level project. Teammates should clone this repository,
then follow the root workspace setup guide for the optional external inputs.
