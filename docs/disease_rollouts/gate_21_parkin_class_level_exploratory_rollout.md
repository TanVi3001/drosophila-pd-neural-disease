# Gate 21: Parkin class-level exploratory disease rollout

## Muc tieu

Gate 21 chay condition `parkin` tren mapping DAN/dopaminergic class-level da duoc reviewer duyet. Day la rollout tham do de kiem tra pipeline neural-to-body, khong phai mapping Parkin gene-specific.

## Protocol khoa

- 5 seed: `0, 1, 2, 3, 4`.
- 5 muc burden: `0.0, 0.25, 0.5, 0.75, 1.0`.
- 25 rollout planned, dung cung physics, timestep, stimulus, CPG va so step voi Healthy baseline Gate 11.
- Timestep `0.0001 s`, `5000` steps, thoi luong vat ly khoang `0.5 s`.
- Video dai dien duoc yeu cau cho burden `0.0` va `1.0`, seed `0`, camera tracking.
- Raw rollout duoc hash sau QC va xoa mac dinh de tiet kiem dung luong; metrics, status, video va manifest duoc giu.

## Neural perturbation

Burden duoc noi suy tu Healthy neural state vao mot bo tham so proxy da khai bao trong config. Gate nay khong gan cac he so nay voi dopamine, Parkin protein hay gia tri literature. Day la mot phep thu sensitivity cua computational disease layer:

- presynaptic gain: `0.75` o full burden;
- postsynaptic gain: `0.75` o full burden;
- neuron survival factor: `0.5` o full burden;
- energy capacity: `0.75` o full burden;
- energy consumption scale: `1.25` o full burden;
- noise va action delay: `0` trong Gate 21.

Tai burden `0`, checkpoint phai trung voi Healthy checkpoint ve logic perturbation. Tai burden duong, checkpoint chi thay doi trong target DAN IDs da co provenance.

## QC va artifact

Moi rollout chi duoc danh dau `PASS` neu co metrics finite, timestamp/timestep hop le, thorax displacement, contact, joint trajectory, action trajectory, observation state va quaternion hop le. Script xuat:

```text
experiments/gate_21_parkin_class_level_rollout/results/
  metrics.csv
  metrics.json
  manifest.json
  checksums.sha256
  report.md
  burden_*/seed_*/
```

## Ranh gioi claim

Gate 21 co the ket thuc o `PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_PASS`, `..._PARTIAL` hoac `..._BLOCKED`. Du status nao cung khong duoc dien giai la Parkin gene-specific validation, biological Parkinson validation, calibration, holdout validation hay bang chung thay the thi nghiem ruoi that.

Chay:

```powershell
py -3.12 scripts/run_gate21_parkin_class_level_rollout.py `
  --brain-root E:\Drosophila_Parkinson\phase-A-clean `
  --platform-root E:\Drosophila_Parkinson\drosophila-pd-flygym `
  --brain-python E:\Drosophila_Parkinson\phase-A-clean\.venv\Scripts\python.exe
```
