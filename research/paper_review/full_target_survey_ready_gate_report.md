# Full target survey and READY gate report

## Current state

- Phạm vi của đợt này là rà soát target locomotion ở *Drosophila melanogaster* liên quan đến Parkinson, không phải systematic review đã đăng và không phải tự động trích xuất dữ liệu.
- Repository được kiểm tra ở nhánh `main`, trước đợt survey là commit `6d80209`.
- Audit trước survey: `WAITING_TARGET_DATA`.
- Audit trước survey: 0 approved target, 0 calibration target hợp lệ, 0 holdout target hợp lệ.
- Kiểm thử trước survey: 58 passed.
- Không chạy calibration, simulation hoặc disease multi-seed trong đợt này.
- Không thêm PDF lớn hoặc raw archive nhiều gigabyte vào repository. Các record giữ URL nguồn primary và ghi rõ trạng thái file cục bộ trong CSV.

## Existing target review

| Paper | Kết quả rà soát | Trạng thái |
|---|---|---|
| [Pokrzywa 2017](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0184117) | Figure 2A báo mean velocity và ±SE; S6 supplementary chỉ có p-value, không có SE số học cho mốc day 21. Số independent vial chỉ được báo ở dạng 3–10. | `PENDING_HUMAN_SIGNOFF`; calibration candidate tốt nhất trong 6 paper nhưng chưa đủ điều kiện. |
| [Pozo 2022](https://www.mdpi.com/2073-4409/11/9/1544) | Pink1B9 distance 62.091 mm, spread 61.288, n=21, Figure 3B; spread được giữ là IQR/max-min theo paper, không đổi thành SD/SE và không đổi distance thành speed. | `SURVEYED_PENDING_TRANSFER`; holdout candidate, chưa approved. |
| [Riemensperger 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3048124/) | Median speed 7.8 mm/s, n=13, age 2–5 ngày; chưa có numeric IQR/range phù hợp schema hiện tại. | `PENDING_HUMAN_SIGNOFF`; không đổi median thành mean. |
| [Hwang 2013](https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1003412) | Climbing assay, mean ± s.e., n tối thiểu được báo; không có target planar walking tương thích. | `VALIDATION_ONLY`. |
| [Godena 2014](https://www.nature.com/articles/ncomms6245) | Climbing/flight với LRRK2, có giá trị sinh học nhưng chưa có endpoint climbing/flight trong FlyGym và chưa có VNC root-ID provenance được duyệt. | `VALIDATION_ONLY`. |
| [Dumitrescu 2023](https://pubmed.ncbi.nlm.nih.gov/36576890/) | DAM beam-break activity theo tuổi; không tương đương walking speed và không được quy đổi. | `NOT_COMPARABLE` cho speed calibration. |

## Expanded literature survey

Đã khảo sát 35 phenotype/target records thuộc 16 DOI/PMCID/source records. Kết quả được lưu trong:

- `research/paper_review/literature_survey_expanded_targets.csv`
- `research/paper_review/full_target_survey_matrix.csv`
- `research/paper_review/target_adjudication_decisions.csv`

Các nguồn bổ sung được đưa vào survey:

- [Chen et al. 2014, adult horizontal walking A30P](https://pmc.ncbi.nlm.nih.gov/articles/PMC4262005/): endpoint đi bộ phù hợp về mặt khái niệm, nam 15/30 ngày, n=23/20, mean ± 95% CI; số mean/CI chính xác chưa được digitize và second-review.
- [Aggarwal et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6900508/): supplementary có mean/SEM/numeric cho assay climbing với đơn vị BLU/s. Các record được giữ `VALIDATION_ONLY`, không đổi BLU/s thành mm/s.
- [Kajtor et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12306971/): Parkin và α-synuclein có speed trước threat và freezing/reactivity; cohort count được báo, nhưng summary số học cần raw archive Figshare lớn chưa được xử lý.
- [Bridi et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8111063/): active-speed theo mốc tuổi được ghi nhận nhưng numeric value/uncertainty chưa xác minh từ supplementary.
- [Cackett et al. 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5469398/): DAM activity có mean/SEM và experiment count, nhưng là endpoint hoạt động không phải planar walking.
- Các nguồn larval, climbing và activity khác được giữ để audit phạm vi hoặc validation; không được dùng thay cho adult FlyGym speed/distance.

Phân loại sau survey:

- 3 record `PENDING_HUMAN_SIGNOFF`.
- 2 record `PENDING_DIGITIZATION`.
- 4 record `PENDING_RAW_DATA_EXTRACTION`.
- 2 record `PENDING_SUPPLEMENTARY_REVIEW`.
- 1 record `SURVEYED_PENDING_TRANSFER`.
- 14 record `VALIDATION_ONLY`.
- 2 record `NOT_COMPARABLE`.
- 4 record `EXCLUDED_OUT_OF_SCOPE`.
- 3 record `SURVEYED_CONTEXT_ONLY`.

Không có record nào được nâng thành approved chỉ vì có p-value, phần trăm thay đổi, bar plot hoặc một đơn vị assay khác.

## Approved calibration target

`NONE`.

Pokrzywa là ứng viên gần nhất với `mean_planar_speed_mm_s`, nhưng chưa thể approved vì:

- numeric SE của day 21 chưa có trong text hoặc S6 supplementary đã kiểm tra;
- số independent vial cụ thể tại day 21 chưa được báo dưới dạng số duy nhất;
- assay-transfer sang endpoint FlyGym chưa được research lead phê duyệt;
- chưa có second-review signoff cho các trường trên.

Chen 2014 là ứng viên bổ sung đáng ưu tiên cho calibration sau này, nhưng hiện còn thiếu giá trị số được digitize, quy tắc chuyển đơn vị cm/s và second review. Không tạo file digitization giả.

## Approved holdout target

`NONE`.

Pozo 2022 là ứng viên holdout mạnh nhất hiện có cho `distance_traveled_mm`:

- center được báo là 62.091 mm;
- spread được giữ đúng là 61.288 theo cách paper báo cáo;
- n=21 fly;
- Figure 3B và DOI/PMID có provenance.

Tuy nhiên, row trong `calibration_targets/targets.csv` vẫn phải giữ pending cho đến khi research lead xác nhận bằng văn bản rằng open-field distance của Pozo được phép transfer sang `distance_traveled_mm` của FlyGym, đồng thời reviewer thực tế, ngày review, allocation và assay transfer được ghi đủ. Không dùng Pozo làm speed target.

## Root-ID mapping status

Không có gene-specific root-ID mapping mới được phê duyệt trong survey.

Các trạng thái hiện tại vẫn phải giữ:

- dopamine class mapping: `CLASS_LEVEL_EXPLORATORY_ONLY`;
- alpha-synuclein và Parkin: `WAITING_REVIEWED_ROOT_ID_MAPPING`;
- PINK1: `MODEL_SCOPE_NOT_CELL_SPECIFIC`;
- DJ-1: `NOT_MAPPABLE_FROM_PAPER`;
- LRRK2: `NOT_MAPPABLE_TO_CURRENT_CONNECTOME`.

Không suy ra root ID từ tên gene, driver hoặc phenotype. Một mapping gene-specific chỉ được đưa vào calibration khi có FlyWire version, root ID, cell type, driver/expression scope, nguồn xác nhận, reviewer và ngày review.

## Audit result

- `targets.csv` không được thay đổi sang approved.
- Approved target count: 0.
- Calibration target count: 0.
- Holdout target count: 0.
- Expected status: `WAITING_TARGET_DATA`.
- Policy được áp dụng: `docs/target_approval_policy.md`.
- Candidate staging vẫn giữ Pokrzywa/Pozo pending và các assay không tương thích ở validation-only hoặc not-comparable.

## Validation result

Các lệnh đã chạy sau khi hoàn tất chỉnh sửa:

```text
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Kết quả thực tế:

- Audit: pass, trạng thái `WAITING_TARGET_DATA`.
- Compileall: pass.
- Pytest: `58 passed`.
- `git diff --check`: pass.

Kết quả hợp lệ của đợt này là audit vẫn `WAITING_TARGET_DATA`, vì không có target nào đủ điều kiện approved. Không được sửa audit để ép `READY_FOR_CALIBRATION`.

## Scientific boundary

Survey này chỉ chuẩn bị dữ liệu cho computational locomotion calibration/validation. Nó không phải biological Parkinson validation, không phải mô hình chẩn đoán, không phải dự đoán lâm sàng, không phải đánh giá thuốc và không thay thế thí nghiệm trên ruồi thật. `READY_FOR_CALIBRATION`, nếu đạt trong tương lai, chỉ có nghĩa là đủ điều kiện chạy phép hiệu chuẩn tính toán với target literature đã được duyệt.

## Required human actions

1. Với Pokrzywa: lấy numeric SE và số vial độc lập chính xác từ S1/dataset gốc hoặc tạo digitization file có ảnh nguồn, tọa độ trục, người digitize và second reviewer.
2. Với Pozo: ký duyệt assay-transfer cho distance, giữ nguyên IQR/max-min, ghi reviewer/date và phân bổ `holdout`.
3. Với Chen: nếu chọn làm calibration, digitize Figure 4 theo policy riêng cho CI95, xác nhận quy đổi cm/s và review độc lập.
4. Ghi reviewer thứ hai, ngày review, unit of analysis và provenance vào các bảng review.
5. Chỉ khi có tối thiểu một target calibration và một target holdout hợp lệ mới chạy audit lại; trước đó không chạy calibration hoặc disease multi-seed.
