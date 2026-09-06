# Runbook sau khi target được phê duyệt

Tài liệu này là phiếu chạy cho nhóm nghiên cứu sau khi reviewer hoàn tất
`calibration_targets/targets.csv`. Nó không tự phê duyệt target, không tạo số liệu
và không bỏ qua runtime/data gate.

## 1. Khóa workspace và kiểm tra runtime

Chạy từ PowerShell tại root repository:

```powershell
py -3.12 --version
& ..\drosophila-pd-flygym\.venv\Scripts\python.exe ..\drosophila-pd-flygym\scripts\check_runtime.py
& ..\drosophila-pd-flygym\.venv\Scripts\python.exe scripts\check_neural_inputs.py `
  --brain-root external\fly-brain `
  --output results\neural_input_status.json
```

Chỉ tiếp tục nếu Python, FlyGym, MuJoCo, neural source và checkpoint đều đạt.
Lưu commit, config, seed, runtime và SHA256 vào manifest của campaign. Không dùng
file có hash khác với provenance đã review.

## 2. Kiểm tra target gate

```powershell
py -3.12 scripts\audit_calibration_targets.py `
  --targets calibration_targets\targets.csv `
  --output results\calibration_readiness
Get-Content results\calibration_readiness\target_audit.md
```

Chỉ khi status là `READY_FOR_CALIBRATION` và có ít nhất một target calibration cùng
một holdout độc lập mới được sang bước tiếp. Nếu status là
`WAITING_TARGET_DATA`, dừng tại đây.

## 3. Chạy disease multi-seed

Chỉ dùng các condition YAML non-template đã có neuron/edge/burden/provenance được
review. Không truyền các file `*.template.yaml` vào campaign để tạo kết quả khoa
học.

```powershell
py -3.12 scripts\run_neural_campaign.py `
  --brain-root external\fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python ..\drosophila-pd-flygym\.venv\Scripts\python.exe `
  --config configs\conditions\<condition-reviewed>.yaml `
  --age-days <age-days> `
  --seeds 0,1,2,3,4 `
  --steps 5000 `
  --device cuda `
  --stimulus p9 `
  --output-root results\disease_campaign\<condition>
```

Mỗi run phải có `status.json`, `manifest.json`, `rollout.npz`, metrics và cùng
physics/timestep/duration với Healthy baseline. Run lỗi phải được giữ log và loại
theo QC, không chạy lại vô hạn để tìm kết quả đẹp.

## 4. So sánh với Healthy

Chỉ ghép cùng seed và cùng metric giữa Healthy và disease run có status `PASS`.
Không dùng các run exploratory khác protocol. Xuất delta tuyệt đối và ghi rõ số
seed hợp lệ, seed bị thiếu và lý do loại.

## 5. Đánh giá calibration và holdout

Với từng artifact metrics đã đạt QC:

```powershell
py -3.12 scripts\evaluate_calibration_holdout.py `
  --metrics results\disease_campaign\<condition>\seed_000\metrics\metrics.json `
  --targets calibration_targets\targets.csv `
  --output results\calibration_evaluation\<condition>\seed_000
```

Script hiện có tính RMSE, MAE, cosine và Huber trên target calibration/holdout đã
duyệt; nó không tự tối ưu tham số. Nếu nhóm cần parameter fitting, đó là một công
việc phương pháp riêng phải được thiết kế và review trước.

## 6. Kiểm tra sau campaign

```powershell
py -3.12 scripts\analyze_healthy_baseline.py `
  --runs-root results\healthy_baseline_reproducible\runs `
  --output results\healthy_baseline_reproducible\summary
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Disease output phải được audit tương đương Healthy trước khi đưa vào comparison,
figure hoặc paper. Mọi artifact cần manifest, checksum, command, seed, config,
runtime và source provenance.

## Ranh giới khoa học

Kết quả chỉ được gọi là computational locomotion response/concordance của một
perturbation. Không gọi là biological Parkinson validation, chẩn đoán, clinical
prediction, drug response hay thay thế thí nghiệm trên ruồi thật.
