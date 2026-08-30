# Báo cáo final gate: Target Adjudication 03

Ngày review: 2026-08-31
Phạm vi: kiểm tra điều kiện promote target, không chạy simulation và không chạy calibration.

## Kết luận

Trạng thái hiện tại vẫn là:

```text
WAITING_TARGET_DATA
```

`READY_FOR_CALIBRATION` chưa đạt một cách hợp lệ. Đây là blocker về dữ liệu và phê duyệt khoa học, không phải lỗi phần mềm.

Không target nào trong `calibration_targets/targets.csv` được đổi sang `approved` trong gate này.

## Kết quả audit

Audit được chạy trên `calibration_targets/targets.csv` và cho kết quả:

- Số dòng target: 2.
- Target approved đủ điều kiện: 0.
- Target calibration hợp lệ: 0.
- Target holdout hợp lệ: 0.
- Trạng thái audit: `WAITING_TARGET_DATA`.

File audit:

```text
results/calibration_readiness/target_audit.md
results/calibration_readiness/target_audit.json
```

## Target calibration

### Pokrzywa alpha-synuclein Day 21

Đây vẫn là ứng viên calibration mạnh nhất hiện tại vì paper báo cáo mean velocity bằng `mm/s` trong FlyTracker.

Bằng chứng hiện có:

- Giá trị trung tâm: `2.5 mm/s`.
- Statistic: mean.
- Uncertainty type được mô tả là `SE`.
- Dữ liệu được thu từ 3--10 independent vials, mỗi vial có 10 female flies.
- Nguồn: Figure 2A/Results của Pokrzywa.

Blocker bắt buộc:

- Chưa có numeric SE.
- Chưa có numeric sample size duy nhất theo unit of analysis được phê duyệt.
- Chưa có `assay_transfer=allowed` cho chuyển đổi FlyTracker vial velocity sang FlyGym `mean_planar_speed_mm_s`.
- Chưa có file `research/paper_review/digitized/pokrzywa_fig2A_day21_speed.csv` hoặc bảng supplementary chứa các giá trị trên.

Quyết định: `PENDING_HUMAN_SIGNOFF`. Không dùng làm calibration target ở gate này.

## Target holdout

### Pozo Pink1B9 Day 28

Đây là ứng viên holdout tốt nhất hiện tại, nhưng chỉ với endpoint distance, không phải speed.

Bằng chứng hiện có:

- Metric: `distance_traveled_mm`.
- Giá trị Pink1B9: `62.091 mm`.
- Spread được paper báo cáo cùng cách trình bày IQR với maximum/minimum ranges: `61.288`.
- Sample size: `21 fly`.
- Nguồn: Figure 3B, DOI `10.3390/cells11091544`, PMID `35563850`.

Blocker bắt buộc:

- `assay_transfer_to_flygym` hiện vẫn là `TRANSFER_REVIEW_REQUIRED`.
- Cần research-lead signoff rằng simulation distance/path-length là endpoint tương thích.
- Cần policy chính thức giữ `61.288` là spread paper-reported IQR/min-max, không đổi thành SD hoặc SE.
- Chưa có allocation holdout được promote trong `targets.csv`.

Quyết định: `PENDING_HUMAN_SIGNOFF`, `holdout_candidate`. Không dùng làm holdout chính thức ở gate này.

## Các record không được promote

- Riemensperger: paper báo cáo median speed; không được đổi thành mean và hiện thiếu spread số học.
- Hwang: climbing assay, giữ `VALIDATION_ONLY`; không đổi thành walking speed.
- Godena: climbing/flight và motor-neuron/VNC scope, giữ `VALIDATION_ONLY`.
- Dumitrescu: DAM beam-break activity, `NOT_COMPARABLE` với planar walking speed.

## Root-ID mapping

Gate này không phê duyệt root ID mới.

Không được suy ra root ID từ tên gene, driver hoặc phenotype. Những scope chưa có provenance FlyWire gene-specific phải tiếp tục giữ trạng thái phù hợp như:

- `WAITING_REVIEWED_ROOT_ID_MAPPING`;
- `NOT_MAPPABLE_FROM_PAPER`;
- `MODEL_SCOPE_NOT_CELL_SPECIFIC`;
- `CLASS_LEVEL_EXPLORATORY_ONLY`.

## Điều kiện để chuyển sang READY

Cần hoàn thiện tối thiểu hai gói bằng chứng độc lập:

### Calibration: Pokrzywa

- numeric SE từ S1 Table hoặc file digitization có provenance;
- numeric sample size theo independent vial;
- reviewer thật và ngày review;
- `assay_transfer=allowed`;
- `allocation=calibration`;
- statistic mean và metric `mean_planar_speed_mm_s` khớp.

### Holdout: Pozo

- giữ metric `distance_traveled_mm`;
- sample size `21`, unit `fly`;
- giữ nguyên loại spread IQR/min-max;
- reviewer thật và ngày review;
- `assay_transfer=allowed` cho distance/path-length;
- `allocation=holdout`;
- không dùng cùng target này cho calibration.

Sau khi đủ các điều kiện trên, cập nhật `targets.csv`, chạy lại audit và chỉ tiếp tục nếu audit trả:

```text
READY_FOR_CALIBRATION
```

## Phạm vi khoa học

Gate này chỉ xác nhận tính đầy đủ và tương thích của target literature cho một phép so sánh computational. Nó không phải biological Parkinson validation, không phải chẩn đoán, không phải dự đoán lâm sàng và không phải thử thuốc.
