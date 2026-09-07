# Gate 21B - Virtual healthy replication

**Trạng thái:** `NOT_EXECUTED_DRY_RUN`

Disease layer: `OFF`. Calibration và tuning: `OFF`.

## Blocker

- `brain_artifact_missing:brain_body_bridge.py`
- `brain_artifact_missing:code/run_pytorch.py`
- `brain_artifact_missing:data/2025_Completeness_783.csv`
- `brain_artifact_missing:data/2025_Connectivity_783.parquet`
- `brain_artifact_missing:data/plastic_weights.pt`
- `dry_run_requested`


Mỗi hàng là một seed độc lập. Frame trong rollout không được dùng như replicate thống kê.
Video (nếu có) chỉ là minh họa cho rollout computational, không là bằng chứng định lượng.
