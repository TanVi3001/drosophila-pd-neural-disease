# Drosophila Parkinson-like Locomotion Proxy

Đây là repository nghiên cứu xây dựng một computational locomotion proxy ở
mức organism-level cho các kiểu hình vận động Parkinson-like trên Drosophila.
Pipeline sử dụng FlyGym/MuJoCo và brain-body runtime để chạy rollout vận động;
không phải mô hình Parkinson sinh học hoàn chỉnh.

## Tóm tắt claim-safe

This project builds a computational locomotion proxy for Drosophila
Parkinson-like phenotypes using FlyGym/MuJoCo rollouts. A Chen-only ratio
calibration selected a locked proxy burden level of 0.5, which was confirmed in
independent reruns. A Pozo PINK1 holdout check showed directional concordance
but substantial quantitative ratio mismatch. The current evidence supports
organism-level computational phenotype concordance, not biological or
gene-specific Parkinson validation.

Nói ngắn gọn, burden `0.5` được chọn bằng Chen-only ratio calibration và được
kiểm tra lại bằng seed độc lập. Pozo chỉ được dùng làm holdout. Holdout cho
thấy distance giảm theo đúng chiều khi burden tăng, nhưng ratio mô phỏng vẫn
lệch lớn so với ratio Pozo.

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
| --- | --- |
| Chen ratio calibration | `CHEN_RATIO_CALIBRATION_PASS` |
| Chen calibrated confirmation | `CHEN_CALIBRATED_CONFIRMATION_PASS` |
| Pozo holdout runtime | `POZO_HOLDOUT_RUNTIME_PASS` |
| Pozo directionality | `PASS` |
| Pozo quantitative ratio match | `NOT SUPPORTED` |
| Claim lock | `ACTIVE` |

## Kết quả chính

| Gate | Mục đích | Status | Kết quả chính | Diễn giải |
| --- | --- | --- | --- | --- |
| Gate 13B | Chen-only ratio calibration | `CHEN_RATIO_CALIBRATION_PASS` | Selected `proxy_burden_level = 0.5` | Candidate gần nhất trên discrete grid, không phải perfect fit |
| Gate 13C | Calibrated confirmation rerun | `CHEN_CALIBRATED_CONFIRMATION_PASS` | Confirmation ratio = `0.6142` | Hành vi của burden đã khóa được tái hiện ở seed độc lập |
| Gate 14B | Pozo holdout run | `POZO_HOLDOUT_RUNTIME_PASS` | `12/12` rollouts pass | Holdout pipeline chạy thành công |
| Gate 14C | Holdout adjudication | `DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH` | Simulated ratio `0.9470` vs Pozo target `0.1920` | Chỉ directional concordance; quantitative mismatch vẫn lớn |

Trong Gate 14B, distance trung bình là `1.66679 mm` ở control burden `0.0` và
`1.57846 mm` ở holdout burden `0.5`. Đây là kết quả của computational runtime
ở thời lượng `0.5 s`, không phải phép quy đổi trực tiếp sang thời gian hay
assay sinh học của paper.

## Phạm vi khoa học

Repository hiện chỉ hỗ trợ các phát biểu sau:

- organism-level computational locomotion proxy;
- Chen-only ratio calibration với burden đã khóa `0.5`;
- calibrated confirmation bằng các seed độc lập;
- Pozo holdout có directional concordance;
- quantitative ratio mismatch được báo cáo rõ ràng.

Không được diễn giải kết quả là:

- biological Parkinson validation;
- gene-specific alpha-synuclein hoặc PINK1 validation;
- clinical validation hoặc diagnostic prediction;
- đánh giá hiệu lực thuốc hoặc can thiệp điều trị;
- quantitative Pozo validation;
- bằng chứng đã xác nhận cơ chế Parkinson.

English boundary: `not biological Parkinson validation`, `not gene-specific
validation`, `not clinical validation`, and `not drug validation`.

Pozo là holdout độc lập, không được dùng để calibration hoặc tune lại
`proxy_burden_level`.

## Cài đặt

Yêu cầu Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

## Kiểm tra artifact và tái lập

Các lệnh dưới đây dùng để xác minh trạng thái và artifact đã có. Không mặc
định chạy lại GPU rollout lớn; các rollout GPU đã có manifest/checksum.

```powershell
py -3.12 scripts/adjudicate_pozo_holdout_claims.py
py -3.12 scripts/prepare_pozo_holdout_protocol.py
py -3.12 scripts/run_chen_ratio_calibration.py
py -3.12 scripts/prepare_chen_only_calibration_objective.py
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Đọc claim lock tại [docs/claims/current_claim_lock.md](docs/claims/current_claim_lock.md)
và báo cáo adjudication tại
[docs/holdout/gate_14c_holdout_adjudication_report.md](docs/holdout/gate_14c_holdout_adjudication_report.md).

## Chuẩn bị condition

Các YAML trong `configs/conditions/` là template. Sau khi có annotation và
target đã được review, có thể kiểm tra edge-list:

```powershell
python scripts/apply_neural_condition.py `
  --config configs/conditions/alpha_synuclein.template.yaml `
  --age-days 20 `
  --annotations annotations/neuron_annotations.csv `
  --edges data/edge_list.csv `
  --output results/alpha_synuclein/day_020
```

Edge CSV phải có đúng các cột `pre_id,post_id,weight`. Lệnh trên chỉ tạo
perturbed edge artifact; nó không chạy FlyGym và không tạo rollout giả.

Kiểm tra brain source ngoài repository:

```powershell
python scripts/check_neural_inputs.py `
  --brain-root E:\Drosophila_Parkinson\phase-A-clean `
  --output results/neural_input_status.json
```

`READY` ở bước này chưa thay thế kiểm tra license, annotation và calibration
target.

## Healthy baseline đa seed

Protocol Healthy nằm tại `configs/healthy_baseline_reproducible.yaml`. Sau khi
có năm rollout seed `0-4`, có thể tổng hợp bằng:

```powershell
python scripts/analyze_healthy_baseline.py `
  --runs-root results/healthy_baseline_reproducible/runs `
  --output results/healthy_baseline_reproducible/summary
```

Script kiểm tra timestamp, NaN/Inf, contact, chuyển động khớp,
quaternion, manifest/SHA256 và rollout trùng; sau đó sinh bảng mean, SD, SE,
bootstrap CI 95% và biểu đồ. Xem [Healthy baseline methods](docs/healthy_baseline_methods_and_evidence.md).

## Brain-body rollout và MP4

Nguồn brain public, checkpoint và checksum được ghi trong
`data/SOURCE_PROVENANCE.md`. Khi đủ license/provenance:

```powershell
python scripts/fetch_brain_source.py --output external/fly-brain
python scripts/check_neural_inputs.py --brain-root external/fly-brain --output results/neural_input_status.json
```

Healthy rollout gọi FlyGym/MuJoCo runner của platform và có thể xuất MP4 thật:

```powershell
python scripts/run_neural_experiment.py `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python C:\path\to\brain-env\python.exe `
  --seed 0 --steps 1000 --device cuda `
  --output results/healthy/seed_000 --video
```

Disease config chỉ được chạy khi có neuron/edge annotation, burden curve và
target literature đã review. Nếu chưa có, runner phải trả trạng thái chờ và
không tạo simulation giả.

## Quy trình nghiên cứu

1. Xác minh license và version của brain source.
2. Điền neuron annotation và provenance.
3. Nhập literature targets đã được review.
4. Chốt healthy checkpoint.
5. Chạy một computational proxy với cùng seed/body/terrain/timestep.
6. Calibration trên target đã chọn.
7. Holdout trên paper/target độc lập.
8. Adjudicate claim trước khi viết báo cáo hoặc bản thảo.
9. Đưa rollout thật sang platform `drosophila-pd-flygym` để phân tích.

## Repository map

- `docs/claims/`: claim lock và hướng dẫn wording.
- `docs/calibration/`: objective, calibration và confirmation reports.
- `docs/holdout/`: Pozo protocol, runtime và adjudication reports.
- `experiments/gate_13b_chen_ratio_calibration/`: Chen calibration artifacts.
- `experiments/gate_13c_calibrated_confirmation/`: confirmation artifacts.
- `experiments/gate_14b_pozo_holdout_validation/`: holdout runtime artifacts.
- `experiments/gate_14c_holdout_adjudication/`: adjudication summary/claim table.
- `scripts/`: kiểm tra, chuẩn bị và chạy workflow hiện có.
- `tests/`: regression tests.

## Tài liệu nền tảng

- [Kiến trúc](docs/01_kien_truc.md)
- [Mô hình neural](docs/02_mo_hinh_neural.md)
- [Disease profiles](docs/03_disease_profiles.md)
- [Calibration](docs/04_calibration.md)
- [GPU](docs/05_gpu.md)
- [Tích hợp nguồn dataset](docs/12_tich_hop_nguon_dataset.md)
- [Dataset candidate và provenance](datasets/README.md)
- [Phenotype literature chờ review](datasets/literature_phenotypes/README.md)
- [Tái lập](docs/06_tai_lap.md)
- [Ranh giới khoa học](docs/07_ranh_gio_khoa_hoc.md)
