# Reproducibility

The repository records code, configuration, review status, and compact
manifests. A real platform rerun must additionally record:

- this repository commit and worktree status;
- platform repository commit and worktree status;
- Python, FlyGym, and MuJoCo versions;
- neural source/checkpoint commit and SHA-256 when used;
- annotations, operator/config hashes, seed, timestep, duration, and output;
- runtime failure logs when execution is unavailable.

Run the source-level preflight first:

```powershell
python scripts/check_platform_contract.py --json
```

The platform owns rollout/export reproducibility. This extension must not
recompute or silently rename platform artifacts. Large raw files stay in
ignored/artifact-storage locations and are referenced by manifests.
