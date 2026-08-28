# Thuc thi neural brain-body

Tai lieu nay mo ta cach noi nguon brain public vao FlyGym dang co. Ma nguon
va du lieu lon khong nam trong Git; xem `data/SOURCE_PROVENANCE.md`.

## License va provenance

- Ma nguon `fly-brain` duoc tai theo commit co dinh va license MIT.
- Connectome FlyWire v783 va annotation co dieu kien su dung rieng. Nhom phai
  kiem tra dieu khoan, trich dan va gioi han phi thuong mai truoc khi cong bo.
- `scripts/fetch_brain_source.py` khong tai theo nhanh troi noi: no kiem tra
  kich thuoc va SHA256 sau moi file.
- `annotations/neuron_annotations.csv` chi ghi chu 18 neuron dich duoc map
  tu bridge public. Cot `region` de trong khi nguon khong cung cap region
  duoc xac nhan.

## Moi truong

Can hai phan phu thuoc:

1. Moi truong platform `drosophila-pd-flygym` co FlyGym, MuJoCo va package
   `drosophila_pd`.
2. Moi truong brain co PyTorch CUDA, pandas, pyarrow va cung co the import
   FlyGym/MuJoCo. Co the cai extra cua repo nay:

```powershell
python -m pip install -e ".[brain,test]"
```

Ban PyTorch CUDA phu thuoc driver NVIDIA va nen cai theo lenh chinh thuc cua
PyTorch cho CUDA dang dung. Kiem tra truoc:

```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
nvidia-smi
```

Khong dung `--device cuda` neu `torch.cuda.is_available()` la `False`.

## Tai va kiem tra input

```powershell
python scripts/fetch_brain_source.py --output external/fly-brain
python scripts/check_neural_inputs.py `
  --brain-root external/fly-brain `
  --output results/neural_input_status.json
```

Checker chi la preflight. `READY` khong co nghia simulation da chay; phai
chay healthy smoke test va kiem tra artifact sau do.

## Healthy rollout co MP4

```powershell
python scripts/run_neural_experiment.py `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python C:\path\to\brain-env\python.exe `
  --seed 0 --steps 1000 --device cuda `
  --output results/healthy/seed_000 `
  --video --video-fps 60 --video-width 960 --video-height 540
```

Output thanh cong do runner platform tao gom rollout, metrics, biomarkers,
`viewer_pose.json`, viewer bundle, manifest va `flygym_rollout.mp4`. Video nay
la ket qua render tu state MuJoCo that, khong phai video tao tu JSON gia.

## Disease condition

Khong dien target bang gia tri vi du. Nhom can review paper, ghi target va
burden curve vao mot YAML rieng. YAML phai co:

- neuron/edge ID co trong annotation va connectome;
- `full_burden` voi tham so da duoc phuong phap nghien cuu phe duyet;
- `burden_curve` theo tuoi;
- provenance paper va trang thai review.

Chay condition sau khi YAML hop le:

```powershell
python scripts/run_neural_experiment.py `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python C:\path\to\brain-env\python.exe `
  --config configs/conditions/pink1.reviewed.yaml `
  --age-days 20 --seed 0 --steps 5000 --device cuda `
  --output results/pink1/day_020/seed_000 `
  --video
```

Runner tao checkpoint perturb tu connectome/weights that, stage tam thoi va
goi runner healthy cua platform voi checkpoint da perturb. Khong sua FlyGym,
MuJoCo hay pipeline khoa hoc goc.

## Nhieu seed va literature

```powershell
python scripts/run_neural_campaign.py `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python C:\path\to\brain-env\python.exe `
  --config configs/conditions/pink1.reviewed.yaml `
  --age-days 20 --seeds 0,1,2,3,4 --steps 5000 `
  --output-root results/campaign/pink1
```

Sau khi co output that, dung `compare_literature_targets.py`. Script chi doc
dong co `review_status=approved`, va tra `WAITING_TARGET_DATA` neu chua co
target so. Khong co phep so sanh nao duoc dien vao tu dong.

## Gioi han

Day la connectome LIF computational ket noi voi locomotion body model. No
khong mo phong dopamine, alpha-synuclein aggregation, chet te bao, gen
expression, duoc dong hoc hay co che benh hoc day du. MP4 va metrics chi duoc
dien giai la computational locomotion evidence.
