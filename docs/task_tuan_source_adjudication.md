# Task giao Tuấn: adjudication nguồn và target literature

## Mục tiêu

Hoàn tất một vòng kiểm tra độc lập đối với corpus paper đã chọn để quyết định record nào có thể trở thành calibration target, record nào chỉ được dùng cho holdout/validation và record nào không thể chuyển sang metric FlyGym. Task này không được tạo số liệu, không phê duyệt bằng suy đoán và không chạy simulation hay calibration.

## Phạm vi đầu vào

- `research/paper_review/selected_sources.csv`
- `research/paper_review/selected_source_manifest.csv`
- `datasets/literature_phenotypes/paper_registry.csv`
- `research/paper_review/paper_analysis_vi.csv`
- `datasets/literature_phenotypes/phenotype_records.csv`
- `datasets/literature_phenotypes/second_review_audit.csv`
- `datasets/literature_phenotypes/root_id_mapping_audit.csv`
- `calibration_targets/targets.csv`
- PDF canonical trong `temporary/paper_pdf/curated_sources/` và PDF đã có trong `temporary/paper_pdf/`

## Quy tắc bắt buộc

1. Mỗi dòng trong `paper_analysis_vi.csv` tương ứng đúng một `record_id`; không gộp nhiều genotype, tuổi, assay hoặc metric.
2. Đọc từ phần Methods, Results, figure, table và supplementary. Nếu không có giá trị số chính xác thì để trống và dùng `PENDING_HUMAN_SIGNOFF`.
3. Giữ nguyên statistic của paper: mean, median, SE/SEM, SD, IQR hoặc range. Không đổi median thành mean, không đổi SE thành SD và không đọc chiều cao cột bằng mắt để tạo số.
4. Ghi rõ unit of analysis: fly, vial, trial, group hoặc animal-level summary. Không lấy số fly trong một vial làm số replicate nếu paper phân tích theo vial.
5. Assay chỉ được chuyển sang target FlyGym khi endpoint, đơn vị, thời lượng, sampling và unit of analysis có thể đối chiếu được. Climbing, flight, DAM activity và survival không tự động thành planar walking speed.
6. `reviewer_2` và `review_date` phải là tên/ngày review thực tế của Tuấn hoặc reviewer được chỉ định, không dùng placeholder.
7. Root ID chỉ được ghi khi có nguồn nêu rõ FlyWire version, root ID, cell type, driver/expression scope và provenance. Không suy ra root ID từ tên gene.

## Hồ sơ phải xử lý

| Paper | Việc phải xác minh | Quyết định mặc định nếu thiếu bằng chứng |
|---|---|---|
| Riemensperger 2011 | DTH/ple genotype, tuổi, giới tính, median speed/negative geotaxis và spread | `VALIDATION_ONLY` hoặc pending; không đưa median vào mean speed. |
| Riemensperger 2013 | Alpha-syn genotype, progression theo tuổi, assay và figure-level values | Pending cho đến khi có numeric uncertainty và unit of analysis. |
| Pokrzywa 2017 | Day 21, velocity, SE số học và vials/flies là replicate nào | Pending nếu chưa xác nhận SE và đơn vị phân tích. |
| Pozo 2022 | Pink1B9 day 28, distance và loại spread | Có thể đề xuất holdout cho `distance_traveled_mm` nếu policy được duyệt; không đổi spread thành SD. |
| Hwang 2013 | DJ-1 genotype và climbing Figure 5E | `VALIDATION_ONLY` khi climbing endpoint chưa implement. |
| Godena 2014 | LRRK2 allele, climbing/flight, motor-neuron/VNC scope | `VALIDATION_ONLY`; không chuyển flight/climbing thành speed. |
| Liu 2008 | LRRK2-G2019S, ddc-GAL4, climbing, tuổi và sample size | Validation/climbing context; target chỉ khi endpoint tương thích. |
| Cha 2005 | Parkin loss-of-function, dopaminergic neuron/loco evidence và số replicate | Pending figure review; không suy ra gene-specific root set. |
| Haywood 2004 | Alpha-syn/parkin co-expression và climbing rescue | Validation-only; đây là rescue/climbing, không phải planar-speed target. |
| Aggarwal 2019 | Heterozygous PD models, sex, climbing/geotaxis and unit | Validation/assay-design evidence; không tự quy đổi sang mm/s. |
| Poddighe 2014 | Pink1B9 age bins and climbing; kiểm tra Expression of Concern | Chỉ validation/context cho tới khi research lead chấp thuận. |
| Dumitrescu 2023 | Full paper và supplement, DAM activity, age and sample unit | `NOT_COMPARABLE` với walking speed. |
| Pugliese 2025 | Preprint, VNC CPG, neuron/circuit provenance | Methods-only, không phải disease target. |
| Liessem 2026 | DopaMeander/MDN, forward-backward walking và turning | Methods/turning context, không tự tạo disease target. |
| NeuroMechFly v2 2024 | Version, runtime, data/code provenance | Platform citation-only. |

## File phải cập nhật

### 1. `research/paper_review/paper_analysis_vi.csv`

Điền các cột hiện có: `genotype`, `age_days`, `sex`, `assay`, `metric`, `unit`, `sample_size`, `figure_table`, `uncertainty_type`, `uncertainty`, `supplementary_status`, `flygym_transfer_status`, `reviewer_2`, `review_date`, `decision`, `notes_vi`.

### 2. `datasets/literature_phenotypes/second_review_audit.csv`

Mỗi phenotype record phải có decision trong tập giá trị:

`APPROVED_FOR_CALIBRATION`, `APPROVED_FOR_HOLDOUT`, `VALIDATION_ONLY`, `NOT_COMPARABLE`, `PENDING_HUMAN_SIGNOFF`.

### 3. `datasets/literature_phenotypes/root_id_mapping_audit.csv`

Chỉ chuyển `mapping_status` sang approved khi có root-ID source, connectome/FlyWire version, cell type, scope, reviewer và ngày review thật. Nếu chưa có thì giữ `CLASS_LEVEL_EXPLORATORY_ONLY` hoặc trạng thái pending.

### 4. `calibration_targets/targets.csv`

Chỉ thêm/cập nhật target với `review_status=approved` khi đồng thời có PDF provenance, metric được policy cho phép, value số, uncertainty số hoặc statistic được policy chấp nhận, sample size số đúng unit of analysis, reviewer, review date và allocation là `calibration` hoặc `holdout`. Phải có ít nhất một target calibration và một holdout độc lập; nếu chưa đủ thì không đổi trạng thái.

## Kiểm tra hoàn thành

Chạy từ root repository:

```powershell
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
py -3.12 scripts/audit_calibration_targets.py
git diff --check
```

Báo cáo kết quả vào `results/calibration_readiness/tuan_source_adjudication_report.md`. Nếu còn bất kỳ trường bắt buộc nào thiếu, trạng thái đúng là `WAITING_TARGET_DATA`, không được ép thành `READY_FOR_CALIBRATION`.

## Tiêu chí bàn giao

- Tất cả record có reviewer và ngày review thật.
- Mọi uncertainty không rõ đều để pending, không bịa.
- Calibration và holdout được tách theo record/paper, không dùng cùng một số liệu cho cả hai.
- Root-ID mapping không chứa suy luận từ gene name.
- Audit chạy được và report nêu chính xác blocker còn lại.
- Không có simulation, calibration hoặc biological claim mới phát sinh từ task này.
