# Gate 06 - Target Promotion and READY_FOR_CALIBRATION

## Baseline

- Ngay lap report: `2026-08-31`.
- Main commit truoc Gate 06: `66461c7` (`Merge target digitization and signoff gate`).
- Gate 05 commit: `2f32519` (`research: prepare target digitization and signoff gate`).
- Audit truoc Gate 06: `WAITING_TARGET_DATA`.
- Approved target truoc Gate 06: `0`.
- Calibration target hop le truoc Gate 06: `0`.
- Holdout target hop le truoc Gate 06: `0`.
- Pytest truoc va trong Gate 06: `58 passed`.
- Khong chay simulation, calibration hoac holdout validation.

## Pham vi va nguyen tac

Gate nay chi kiem tra kha nang promotion cua cac candidate da co trong Gate 05.
Khong tu tao human signoff, khong suy dien uncertainty/sample size, khong doi
statistic, khong doi endpoint va khong sua audit script de ep trang thai
`READY_FOR_CALIBRATION`.

Trong repository/task hien tai khong co `REVIEWER_NAME` va `REVIEW_DATE` that
duoc cung cap cho bat ky target nao. Vi vay khong target nao duoc promote.

## Kiem tra human signoff

### Ket qua

- Reviewer signoff cu the: **chua co**.
- Review date cu the dang `YYYY-MM-DD`: **chua co**.
- Pozo signoff form van o trang thai `TRANSFER_REVIEW_REQUIRED`.
- Chen va Pokrzywa van co `PENDING_HUMAN_SIGNOFF` trong file digitization.
- Khong duoc dien ten nguoi chay task thanh reviewer khi chua co uy quyen va
  thong tin signoff tu research lead.

Vi thieu hai truong bat buoc tren, khong co phat bieu nao trong report nay duoc
hieu la human approval.

## Calibration target decision

### Chen 2014 - candidate uu tien

**Quyet dinh:** `PENDING_HUMAN_SIGNOFF`; chua promote.

Du lieu dang co:

- Adult horizontal walking speed/velocity.
- Old A30P: `0.4875 cm/s`, digitized CI95 `0.0525 cm/s`.
- Old CT: `0.7275 cm/s`, digitized CI95 `0.135 cm/s`.
- `n=20`, `sample_unit=fly`, age/timepoint `30`, sex `male` theo candidate.
- Quy doi don vi neu duoc duyet: `1 cm/s = 10 mm/s`.

Thieu de promote:

- Reviewer that va `review_date` that.
- Second review doc lap cho gia tri digitization tu raster.
- `assay_transfer=allowed` cho endpoint walking speed/velocity.
- Policy xac nhan viec dung CI95 lam uncertainty trong target schema; khong doi
  CI95 thanh SE neu khong co cong thuc va signoff phu hop.
- Provenance/signoff cu the cho row se dua vao `targets.csv`.

### Pokrzywa 2017 - fallback calibration candidate

**Quyet dinh:** `PENDING_HUMAN_SIGNOFF`; chua promote.

Du lieu dang co:

- Day 21 mean speed: `2.5 mm/s`.
- Figure-derived SE xap xi `0.12 mm/s`.
- Paper neu `3-10 independent vials`, khong co mot exact vial count cho
  endpoint day 21 trong artifact hien tai.

Thieu de promote:

- Numeric SE tu supplementary/table hoac policy digitization duoc phe duyet.
- Exact numeric sample size theo dung unit of analysis `independent_vial`.
- Reviewer that va `review_date` that.
- `assay_transfer=allowed` va xac nhan age endpoint.
- Provenance/signoff cu the cho row se dua vao `targets.csv`.

Khong duoc dung khoang `3-10` lam sample size so hoc va khong duoc coi
`SE_figure_digitized` la SE nguon neu chua co signoff.

## Holdout target decision

### Pozo 2022 - Pink1B9 distance

**Quyet dinh:** `PENDING_HUMAN_SIGNOFF`; chua promote.

Du lieu dang co:

- `metric=distance_traveled_mm`.
- `value=62.091 mm`.
- `variance_type=IQR_with_min_max_ranges_reported`.
- `variance=61.288`, giu nguyen spread paper-reported.
- `sample_size=21`, `sample_unit=fly`.
- `age_days=28`, genotype `Pink1B9`, Figure 3B.
- DOI/PMID: `10.3390/cells11091544; PMID:35563850`.

Thieu de promote:

- Reviewer that va `review_date` that.
- Quyet dinh human ro rang `assay_transfer=allowed` cho distance/path-length.
- Explicit holdout signoff cua research lead.
- Provenance/signoff phu hop trong row approved.

Pozo khong duoc dung lam speed target, khong duoc doi IQR/min-max thanh SD/SE
va khong duoc dung cung cohort cho calibration.

## `targets.csv` update

Khong cap nhat `calibration_targets/targets.csv` trong Gate 06.

Ly do:

- Hien tai file chi co hai row va ca hai deu `review_status=pending`.
- Chua co target approved nao co reviewer, review date, allocation va
  `assay_transfer=allowed`.
- Chua co dong calibration va holdout cung du dieu kien de mo readiness gate.

Cac row pending hien tai:

1. `riemensperger_2011_dopamine_deficiency`: median speed, thieu numeric
   IQR/range va chua co transfer/signoff.
2. `pokrzywa_2017_alpha_syn_flytracker`: thieu age day cu the trong target
   chinh, numeric uncertainty va numeric independent-vial sample size.

Chen va Pozo van nam trong `target_promotion_candidates.csv`, nhung chua duoc
copy vao `targets.csv` vi chua du human signoff.

## Audit result

- Audit command: `py -3.12 scripts/audit_calibration_targets.py`.
- Audit status: `WAITING_TARGET_DATA`.
- Approved target count: `0`.
- Eligible calibration target count: `0`.
- Eligible holdout target count: `0`.
- Blocker: chua co target approved du metadata va provenance de calibration;
  chua co allocation calibration/holdout hop le.

`READY_FOR_CALIBRATION` chua dat va khong duoc ep dat trong Gate 06.

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS.
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS, `58 passed`.
- `git diff --check`: PASS.
- CSV Gate 05 da duoc parse va kiem tra schema trong task truoc; khong them
  row approved trong Gate 06.

## Hanh dong can co de mo gate

Research lead/reviewer thu hai can bo sung vao cac form signoff:

1. Ten reviewer that.
2. Ngay review that theo `YYYY-MM-DD`.
3. Xac nhan uncertainty dung theo paper, khong doi loai statistic.
4. Xac nhan sample size va unit of analysis.
5. Xac nhan `assay_transfer=allowed` cho endpoint cu the.
6. Chon duy nhat mot allocation: `calibration` hoac `holdout`.
7. Ghi provenance den figure/table/supplementary hoac file digitization.

Sau khi co signoff hop le:

- Chen co the la calibration candidate uu tien neu CI95 policy va transfer duoc
  duyet.
- Pozo co the la holdout distance candidate neu research lead phe duyet
  transfer.
- Pokrzywa chi la calibration fallback khi co exact independent-vial count va
  uncertainty duoc phe duyet.

Chi sau khi cap nhat target voi evidence that moi duoc chay lai audit. Gate nay
khong chay calibration, disease simulation hay holdout validation.

## Ranh gioi khoa hoc

`READY_FOR_CALIBRATION`, neu dat o gate sau, chi co nghia la du target literature
cho computational calibration. No khong phai biological Parkinson validation,
khong phai clinical diagnosis, khong phai drug efficacy validation va khong thay
the wet-lab experiment.
