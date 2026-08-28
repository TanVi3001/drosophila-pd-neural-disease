# Drosophila PD Neural Disease

Đây là repository nghiên cứu mở rộng cho nền tảng
[`drosophila-pd-flygym`](https://github.com/TanVi3001/drosophila-pd-flygym).
Mục tiêu là kiểm tra các **neural perturbation có ràng buộc bằng bằng chứng**
trên mô hình locomotion Drosophila, sau đó ghép kết quả với brain-body
pipeline hiện có.

## Phạm vi

Repository này không tự chứa connectome, checkpoint hoặc dataset thực nghiệm.
Các file đó phải được nhóm nghiên cứu cung cấp với license, provenance và
SHA256 rõ ràng. Không có các đầu vào này, workflow dừng ở trạng thái
`WAITING_TARGET_DATA`, `WAITING_ANNOTATION_DATA` hoặc `WAITING_BRAIN_DATA`.

Đây không phải là mô hình Parkinson sinh học hoàn chỉnh, mô phỏng dopamine,
mô phỏng alpha-synuclein aggregation, mô hình chẩn đoán, dự đoán lâm sàng hay
mô hình đáp ứng thuốc. Kết quả chỉ được diễn giải trong phạm vi
computational locomotion simulation.

## Liên hệ với platform

Platform nền tảng cung cấp FlyGym/MuJoCo, brain-body bridge, recorder, viewer,
analysis và biomarker. Repository này cung cấp:

- neuron và edge annotation có provenance;
- disease profile theo genotype và tuổi;
- perturbation theo neuron/edge, không fallback theo tensor index;
- loss RMSE, MAE, cosine và Huber;
- manifest và checksum;
- template calibration, multi-seed và holdout.

## Cài đặt

Yêu cầu Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

## Kiểm tra

```powershell
python -m compileall -q src scripts tests
pytest -q -rs -p no:cacheprovider
git diff --check
```

## Chuẩn bị condition

Các YAML trong `configs/conditions/` chỉ là template. Sau khi có annotation và
target đã được review, có thể kiểm tra edge-list thật:

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

Kiểm tra brain source ngoài repository trước khi tích hợp:

```powershell
python scripts/check_neural_inputs.py `
  --brain-root E:\Drosophila_Parkinson\phase-A-clean `
  --output results/neural_input_status.json
```

Lệnh chỉ kiểm tra file và trả `READY` hoặc `WAITING_BRAIN_DATA`. `READY` chưa
thay thế bước kiểm tra license, annotation và calibration target.

## Quy trình nghiên cứu

1. Xác minh license và version của brain source.
2. Điền neuron annotation và provenance.
3. Nhập literature targets đã được review.
4. Chốt healthy checkpoint.
5. Chạy một gene model với cùng seed/body/terrain/timestep.
6. Calibration trên target đã chọn.
7. Holdout trên paper/target độc lập.
8. Đưa rollout thật sang platform `drosophila-pd-flygym` để phân tích.

## Tài liệu

- [Kiến trúc](docs/01_kien_truc.md)
- [Mô hình neural](docs/02_mo_hinh_neural.md)
- [Disease profiles](docs/03_disease_profiles.md)
- [Calibration](docs/04_calibration.md)
- [GPU](docs/05_gpu.md)

## Chay brain-body that va MP4

Nguon brain public, checkpoint va checksum duoc ghi trong
`data/SOURCE_PROVENANCE.md`. De tai nguon theo commit co dinh:

```powershell
python scripts/fetch_brain_source.py --output external/fly-brain
python scripts/check_neural_inputs.py --brain-root external/fly-brain --output results/neural_input_status.json
```

Healthy rollout goi FlyGym/MuJoCo runner cua platform va co the xuat MP4 that:

```powershell
python scripts/run_neural_experiment.py `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python C:\path\to\brain-env\python.exe `
  --seed 0 --steps 1000 --device cuda `
  --output results/healthy/seed_000 --video
```

Moi truong brain can PyTorch CUDA, pandas, pyarrow, FlyGym va MuJoCo. Cai
phan phu thuoc Python cua repo nay bang `python -m pip install -e ".[brain,test]"`;
ban PyTorch CUDA can chon phu hop voi driver NVIDIA.

Disease config chi duoc chay khi co neuron/edge annotation, burden curve va
target literature da review. Neu chua co, runner tra `WAITING_TARGET_DATA` va
khong chay simulation. `run_neural_campaign.py` ho tro nhieu seed; MP4 duoc
tao tu render MuJoCo that. Moi output chi duoc dien giai la computational
locomotion, khong phai biological Parkinson validation, diagnosis, clinical
prediction hay drug response.
- [Tái lập](docs/06_tai_lap.md)
- [Ranh giới khoa học](docs/07_ranh_gio_khoa_hoc.md)
