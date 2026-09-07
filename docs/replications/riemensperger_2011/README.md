# Pipeline tái lập computational Riemensperger 2011

Phạm vi của study là **paper-guided computational replication of neural
dopamine-deficiency locomotion in virtual Drosophila**. Đây không phải mô hình
Parkinson sinh học, gene-specific validation, chẩn đoán, thử thuốc hoặc thay
thế thí nghiệm ruồi thật.

## Chạy theo gate

```powershell
py -3.12 scripts/run_riemensperger2011_replication_pipeline.py --stage evidence --dry-run
py -3.12 scripts/run_riemensperger2011_replication_pipeline.py --stage healthy --dry-run
py -3.12 scripts/run_riemensperger2011_replication_pipeline.py --stage mapping
py -3.12 scripts/run_riemensperger2011_replication_pipeline.py --stage all --dry-run
```

`--dry-run` chỉ kiểm tra contract, checksum, runtime và blocker; nó không chạy
GPU. Pipeline hiện dừng ở Gate 21D cho đến khi reviewer thứ hai xác nhận mapping
class-level dopamine trong:

```text
research/replications/riemensperger_2011/mapping/dopamine_mapping_spec.yaml
```

Checksum artifact được tạo bằng:

```powershell
py -3.12 scripts/write_riemensperger2011_checksums.py
```

Mỗi thư mục `experiments/gate_21*` có `manifests/checksums.sha256`. File này chỉ
hash artifact nhỏ đã commit; không đưa rollout raw, checkpoint, video hoặc dữ
liệu external vào repository.

Khi mapping được ký duyệt, chạy healthy và disease bằng cùng seed `0..4`,
physics, timestep, controller và duration. Disease runner materialize
checkpoint con bằng module
`drosophila_pd_neural.riemensperger2011.dopamine_transform` rồi mới gọi
`scripts/run_neural_experiment.py` và runner FlyGym công khai.

## Evidence đã khóa

Nguồn chính là DOI `10.1073/pnas.1010930108`, PMID `21187381`, bản full text
PMC. Primary control là `DTHg; ple`; disease là `DTHgFS±; ple`; WT chỉ là
secondary reference. Speed và distance đều được giữ là median. Variance không
được paper báo cáo trong evidence lock thì giữ `NOT_REPORTED`.

## Kết quả và claim

Kết quả cuối chỉ có thể được sinh sau rollout thật và QC. Nếu virtual disease
đi cùng chiều nhưng lệch magnitude, claim được phép là:

> Riemensperger 2011-guided dopamine-class computational perturbation reproduced
> the direction of locomotor impairment in the virtual fly, while substantial
> quantitative mismatch remained.

Không dùng video thay cho thống kê và không xem frame là replicate độc lập.
