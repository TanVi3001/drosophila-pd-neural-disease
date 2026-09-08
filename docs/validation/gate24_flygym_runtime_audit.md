# Gate24 FlyGym runtime audit

## Kết luận

Runtime FlyGym canonical đang ở commit `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`, nhưng worktree chính bị dirty. Không reset, checkout, clean, stash hoặc xóa thay đổi local. Một worktree sạch detached đã được tạo tại:

`E:/Drosophila_Parkinson/drosophila-pd-flygym-gate24-clean`

Worktree sạch:

- `platform_commit`: `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`
- `git_status_clean`: `true`
- `FlyGym`: `2.1.0` theo runtime lock của Gate24
- `MuJoCo`: `3.9.0` theo runtime lock của Gate24
- Python: `3.12.10` theo runtime lock của Gate24

## Worktree chính

- Path: `E:/Drosophila_Parkinson/drosophila-pd-flygym`
- Branch: `main`
- Commit: `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`
- Trạng thái: dirty

## Phân loại file dirty

| File/nhóm | Phân loại | Có bắt buộc cho Gate24 không? | Nhận xét |
| --- | --- | --- | --- |
| `scripts/run_brain_body_rollout.py` | `REQUIRED_FOR_GATE24_RUNTIME` nhưng chỉ dùng qua clean worktree | Không dùng bản dirty | Có thay đổi video/action-hook/streaming; không đưa vào runtime pin. |
| `scripts/build_viewer_bundle.py` | `UNRELATED_LOCAL_WORK` | Không | Sửa phục hồi viewer và đóng gói artifact. |
| `src/drosophila_pd/analysis/rollout_analysis.py` | `UNRELATED_LOCAL_WORK` | Không | Tối ưu đọc NPZ/JSON cho rollout dài. |
| `src/drosophila_pd/flygym_adapter/export.py` | `UNRELATED_LOCAL_WORK` | Không | Streaming JSON export. |
| `src/drosophila_pd/viewer_export/pose_exporter.py` | `UNRELATED_LOCAL_WORK` | Không | Streaming pose export. |
| `docs/brain_body_gpu_workflow.md` | `UNRELATED_LOCAL_WORK` | Không | Tài liệu video/demo. |
| `notebooks/colab/30_Brain_Body_GPU_Demo.ipynb` | `UNRELATED_LOCAL_WORK` | Không | Notebook/demo và output cell. |
| `tests/test_analysis_pipeline.py` | `UNRELATED_LOCAL_WORK` | Không | Regression cho tối ưu export/NPZ. |
| `tests/test_brain_body_runner.py` | `UNRELATED_LOCAL_WORK` | Không | Regression video và memory release. |
| `tests/test_viewer_bundle.py` | `UNRELATED_LOCAL_WORK` | Không | Regression viewer bundle. |
| `configs/experiments/30_day_campaign.yaml` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal campaign. |
| `docs/longitudinal_campaign.md` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal campaign. |
| `scripts/export_longitudinal_report.py` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal report. |
| `scripts/run_longitudinal_campaign.py` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal campaign. |
| `scripts/visualize_longitudinal_campaign.py` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal visualization. |
| `tests/test_longitudinal_campaign.py` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal tests. |
| `tests/test_longitudinal_visualization.py` | `UNRELATED_LOCAL_WORK` | Không | Longitudinal tests. |

## Reproducibility risk

Nếu chạy Gate24 bằng worktree chính, video/export/action-hook thay đổi có thể làm kết quả không tái lập theo commit `3ceb8ce`. Gate24 phải dùng worktree sạch, đồng thời ghi lại commit, Python, FlyGym và MuJoCo trước GPU. Các thay đổi dirty vẫn được giữ nguyên cho công việc local khác.

## Quyết định

Gate24 có clean pinned platform runtime. Không có file dirty nào được đưa vào runtime pin. Neural transform phải được tích hợp và kiểm tra trên worktree sạch trước khi mở Gate24E; không chạy GPU trong audit này.
