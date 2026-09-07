# Gate 24: Concordance analysis va bang chung cho bai bao

**Trang thai:** `CONCORDANCE_REPORT_COMPLETE`

Gate 24 la phan tich hau nghiem tren artifact da khoa tu Gate 13B, 13C, 21, 22 va 23. Gate nay khong chay GPU, simulation, calibration, holdout validation hoac tuning moi.

## Cau hoi phan tich

- Parameter Chen da khoa co duoc xac nhan lai khong? Co, o muc computational confirmation.
- Proxy co tao ra thay doi van dong co QC khong? Co, nhung pham vi la organism/class-level exploratory.
- Co phu hop voi Pozo ve huong thay doi khong? Co, distance giam duoi burden 0.5.
- Co phu hop dinh luong voi Pozo khong? Khong; quantitative ratio mismatch van lon.

## Concordance matrix

| Evidence | Stage | Status | Metric | Observed | Target | Error | Scope | Claim status |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| chen_calibration | calibration | `PASS` | `mean_planar_speed_ratio` | 0.5856211861021032 | 0.6701030927835051 | 0.08448190668140187 | `organism_level_proxy` | `allowed_computational_calibration` |
| chen_confirmation | confirmation | `PASS` | `mean_planar_speed_ratio` | 0.6142225784195846 | 0.6701030927835051 | 0.0558805143639205 | `organism_level_proxy` | `allowed_computational_confirmation` |
| gate21_rollout | exploratory_rollout | `PASS` | `passed_rollouts` | 25 | 25 | 0.0 | `class_level_exploratory` | `allowed_runtime_evidence` |
| gate22_comparison | healthy_comparison | `PASS` | `comparison_rows` | 55 | 55 | 0.0 | `class_level_exploratory` | `allowed_runtime_evidence` |
| pozo_directionality | holdout | `PASS` | `distance_directionality` | 0.9470070897697126 | < 1.0 | 0.7549687136415942 | `organism_level_proxy` | `allowed_directional_concordance` |
| pozo_quantitative_ratio | holdout | `MISMATCH` | `distance_ratio_to_control` | 0.9470070897697126 | 0.19203837612811836 | 0.7549687136415942 | `organism_level_proxy` | `mismatch_reported` |
| gene_specific_validation | scope | `NOT_AVAILABLE` | `gene_specific_mapping` | false | required | NA | `class_level_exploratory` | `forbidden_positive_claim` |
| biological_parkinson_validation | scope | `NOT_AVAILABLE` | `biological_validation` | false | required | NA | `computational_only` | `forbidden_positive_claim` |

## Thong ke

Gate 22 cung cap mean, sample SD, SE, delta, relative change va paired standardized delta cho 5 seed ghep cap. Khong tinh p-value va khong xem seed la mau sinh hoc doc lap. Pozo ratio mismatch duoc bao cao theo artifact da khoa; khong dat tolerance hau nghiem.

## Claim duoc phep dung

> Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout concordance and substantial quantitative ratio mismatch.

## Claim bi cam

- Biological Parkinson validation.
- Gene-specific PINK1 validation.
- Quantitative Pozo validation.
- Clinical validation.
- Drug efficacy validation.

## Hinh va artifact

- `results/figures/chen_ratio_concordance.png`: Chen target, calibration va confirmation.
- `results/figures/gate22_burden_response.png`: Healthy va Parkin proxy theo burden.
- `results/figures/pozo_ratio_concordance.png`: simulated ratio va Pozo ratio.
- `results/figures/pozo_directionality.png`: control va burden 0.5.
- `results/figures/qc_claim_matrix.png`: QC/provenance/claim matrix.

## Gioi han

Ket qua hien tai phu hop voi mot bai computational locomotion proxy co calibration va holdout directionality, khong phai bang chung thay the thi nghiem ruoi that. Quantitative mismatch voi Pozo la ket qua can duoc giu nguyen trong manuscript, khong duoc lam mem hoac bo qua.
