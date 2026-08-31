# Target Digitization + Signoff Gate 05

## Baseline

- Main commit trước task: `71d343b`.
- Audit trước task: `WAITING_TARGET_DATA`.
- Approved target trước task: `0`.
- Calibration target hợp lệ trước task: `0`.
- Holdout target hợp lệ trước task: `0`.
- Pytest trước task: `58 passed`.
- Survey mở rộng đã có trên main; task này không survey lại từ đầu.
- Không chạy disease simulation, calibration hoặc holdout validation.

## Candidate calibration

### Chen 2014

[Chen et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4262005/) dùng adult *Drosophila* trong horizontal open-field walking, theo dõi ở 17 fps. Figure 4f báo walking velocity cho nhóm Old CT và Old A30P, với `n=20` cho nhóm old và mean ± 95% CI.

Đã tạo `research/paper_review/digitized/chen_2014_adult_walking_speed.csv` với phép đo raster có thể truy nguyên:

- Old A30P: khoảng `0.4875 cm/s`, CI95 khoảng `0.0525 cm/s`.
- Old CT: khoảng `0.7275 cm/s`, CI95 khoảng `0.135 cm/s`.
- Trục: `0–1.2 cm/s`, pixel trục `271–431`.
- Giá trị chuyển đơn vị trong promotion table: `4.875 mm/s` và CI95 `0.525 mm/s` cho Old A30P, dùng quy đổi vật lý `1 cm/s = 10 mm/s`.

Chen chưa được approve vì:

- số liệu được digitize từ raster, cần independent second review;
- uncertainty là `CI95`, trong khi audit target hiện tại chỉ cho phép các loại variance đã định nghĩa trong policy/schema;
- assay-transfer từ horizontal open field sang endpoint FlyGym chưa có signoff thật;
- reviewer và review_date thật chưa được điền.

Quyết định: `PENDING_HUMAN_SIGNOFF`, không cập nhật thành approved.

### Pokrzywa 2017

[Pokrzywa et al. 2017](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0184117) báo mean velocity `2.5 mm/s` cho alpha-synuclein ở mốc day 21 và figure legend ghi error bar ±SE. S6 supplementary đã kiểm tra nhưng không có numeric SE tương ứng; bài báo chỉ nêu `3–10 independent vials`.

Đã tạo `research/paper_review/digitized/pokrzywa_fig2A_day21_speed.csv`:

- Alpha-synuclein day 21: mean `2.5 mm/s`, figure-derived SE xấp xỉ `0.12 mm/s`.
- Control day 21: mean `5.0 mm/s`, figure-derived SE xấp xỉ `0.14 mm/s`.
- Các pixel bar/error bar và trục `0–8 mm/s` được lưu trong file.

Pokrzywa vẫn chưa được approve vì:

- SE là ước lượng từ raster, không phải numeric SE do paper cung cấp;
- số independent vial chính xác tại day 21 chưa có;
- `SE_figure_digitized` không được giả định là SE nguồn;
- assay-transfer và second review chưa được ký.

Quyết định: `PENDING_HUMAN_SIGNOFF`.

## Candidate holdout

### Pozo 2022 distance

[Pozo et al. 2022](https://www.mdpi.com/2073-4409/11/9/1544) cung cấp candidate Pink1B9 ở day 28:

- metric: `distance_traveled_mm`;
- center: `62.091 mm`;
- spread: `61.288`, giữ nguyên cách paper biểu diễn IQR với min/max;
- sample size: `21 fly`;
- provenance: Figure 3B, DOI `10.3390/cells11091544`, PMID `35563850`.

Pozo không được dùng làm speed target. Signoff file đã tạo tại `research/paper_review/pozo_distance_holdout_signoff.md`, hiện trạng `TRANSFER_REVIEW_REQUIRED`.

Pozo chưa được approve vì còn thiếu:

- tên reviewer thật;
- ngày review thật;
- quyết định assay transfer rõ ràng cho distance/path-length;
- explicit holdout signoff của research lead.

Quyết định: `PENDING_HUMAN_SIGNOFF`.

## Target promotion decision

Đã tạo `research/paper_review/target_promotion_candidates.csv` với ba candidate:

| Candidate | Allocation | `ready_to_promote` | Blocker chính |
|---|---|---:|---|
| Chen Old A30P walking speed | calibration | `false` | CI95 policy, second review, assay transfer, reviewer/date |
| Pokrzywa alpha-syn day 21 speed | calibration | `false` | exact vial count, figure-derived uncertainty, second review, assay transfer |
| Pozo Pink1B9 distance | holdout | `false` | explicit human signoff, assay transfer, reviewer/date |

`calibration_targets/targets.csv` không được cập nhật sang `approved`. Không target nào đủ điều kiện để ghi vào audit như approved target.

## Root-ID boundary

Không thêm root ID mới. Các giới hạn hiện tại được giữ nguyên:

- dopamine: class-level exploratory;
- alpha-synuclein và Parkin: chờ reviewed root-ID mapping;
- PINK1: model scope không cell-specific;
- DJ-1: không map được từ paper hiện có;
- LRRK2: chưa map được vào connectome hiện tại.

Không suy ra root ID từ gene, driver hoặc phenotype.

## Audit result

- Audit sau task: `WAITING_TARGET_DATA`.
- Approved target count: `0`.
- Calibration target count: `0`.
- Holdout target count: `0`.
- Không sửa audit script để ép pass.
- Không có `READY_FOR_CALIBRATION` vì chưa có cả một calibration target và một holdout target được human signoff đầy đủ.

## Validation

- `py -3.12 scripts/audit_calibration_targets.py`: pass, `WAITING_TARGET_DATA`.
- `py -3.12 -m compileall -q src scripts tests`: pass.
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: `58 passed`.
- `git diff --check`: pass.
- Digitization CSV: Chen 2 rows/29 columns; Pokrzywa 2 rows/28 columns.
- Promotion CSV: 3 rows/24 columns.

## Scientific boundary

Gate này chỉ đánh giá readiness cho computational calibration. Các con số digitization là candidate có provenance và độ chính xác giới hạn bởi raster, không phải số đo mới từ ruồi thật. Kết quả không phải biological Parkinson validation, không phải chẩn đoán, không phải dự đoán lâm sàng, không phải drug efficacy validation và không thay thế thí nghiệm wet-lab.

## Bước bắt buộc tiếp theo

1. Research lead hoặc reviewer thứ hai kiểm tra ảnh gốc Chen/Pokrzywa và xác nhận/điều chỉnh pixel measurements.
2. Xác nhận policy xử lý CI95 của Chen; không tự đổi CI95 thành SE nếu chưa có policy và review.
3. Xác nhận exact independent-vial count của Pokrzywa day 21 nếu có trong raw source; nếu không có thì giữ pending.
4. Điền tên reviewer thật, ngày review thật và `assay_transfer=allowed` cho Pozo nếu distance endpoint được chấp nhận.
5. Chỉ sau khi các trường trên hợp lệ mới cập nhật `targets.csv`, chạy audit lại và xem xét `READY_FOR_CALIBRATION`.
