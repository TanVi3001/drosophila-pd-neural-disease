# LIF → FlyGym end-to-end bridge

## Trạng thái

Pipeline đã chạy được local vào ngày 2026-09-15:

```text
Brian2 spike parquet
  → build_bridge_scales.py
  → bridge_scales.json (hash + readout summary)
  → run_brain_driven_experiment.py
  → paired healthy/perturbed FlyGym report
```

Artifact kiểm chứng:

- `../../drosophila-pd-flygym/results/end_to_end_20260915/bridge_scales.json`
- `../../drosophila-pd-flygym/results/end_to_end_20260915/platform_report.json`
- `../../drosophila-pd-flygym/results/end_to_end_20260915/pipeline_manifest.json`

Manifest ghi nhận `platform_overall_pass=true`. Bridge ghi nhận
`PASS_WITH_READOUT_GAPS`: stimulus JON-CE 220 Hz có một forward-DN readout,
nhưng không tạo readout cho hai nhóm turn đã review; vì vậy
`coupling_scale=1.0` chỉ là fallback computational được bật rõ bằng
`--allow-missing-turn`.

## Chạy lại

Từ thư mục `drosophila-pd-neural`, với Brian2 output đã tồn tại:

Từ bản sửa v0.1, mỗi spike output phải đi kèm run manifest theo schema
`lif-run-manifest-1` với `trial_count` là số trial đã chạy. Bridge không còn
suy số trial từ các trial có spike; vì vậy lệnh lịch sử dưới đây cần bổ sung
hai tham số manifest trước khi chạy lại. Artifact ngày 2026-09-15 được giữ là
artifact lịch sử, không tự động tái tạo với contract mới.

```powershell
& ..\.venvs\baseline-2024-312\Scripts\python.exe scripts\run_lif_to_flygym.py `
  --reference-spikes ..\external\Drosophila_brain_model\results\reproduce_20260915\bridge_jon_ce_220hz_1trial\JON_CE_220Hz_bridge_1trial.parquet `
  --condition-spikes ..\external\Drosophila_brain_model\results\reproduce_20260915\bridge_jon_ce_110hz_1trial\JON_CE_110Hz_bridge_1trial.parquet `
  --reference-manifest path\to\reference.run.json `
  --condition-manifest path\to\condition.run.json `
  --model jon_ce_drive_reduction_demo `
  --condition-label jon_ce_110hz_vs_220hz `
  --allow-missing-turn `
  --platform-python ..\.venvs\flygym-runtime-312\Scripts\python.exe `
  --output ..\drosophila-pd-flygym\results\end_to_end_20260915
```

Để tạo riêng bridge JSON, dùng `scripts/build_bridge_scales.py`. Không nên
đưa scale vào diễn giải bệnh học nếu readout group còn thiếu hoặc chưa có
validation độc lập.

## Ranh giới khoa học

Bridge này là adapter định lượng giữa hai simulator: tỷ số firing rate của
nhóm neuron được review được dùng làm proxy cho action scale/CPG scale. Nó
không chứng minh motor command sinh học, không tái tạo bệnh Parkinson, và
không thay thế validation bằng ruồi thật.
