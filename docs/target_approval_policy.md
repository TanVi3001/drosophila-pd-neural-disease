# Chính sách phê duyệt target cho calibration

## Mục đích

Chính sách này quy định điều kiện tối thiểu để một endpoint từ y văn được đưa
vào calibration hoặc holdout. Việc một paper có phenotype vận động không đồng
nghĩa endpoint của paper tương thích với metric FlyGym.

Chính sách không tự phê duyệt target, không quy đổi statistic, không chạy
simulation và không xác nhận mô hình Parkinson sinh học.

## Statistic được chấp nhận

Các nhãn statistic được phép ghi nhận là:

- `mean`: giá trị trung bình.
- `median`: trung vị.
- `SE` hoặc `SEM`: sai số chuẩn của trung bình.
- `SD`: độ lệch chuẩn.
- `IQR`: khoảng tứ phân vị.
- `range`: khoảng giá trị được paper báo cáo.

Không đổi `median` thành `mean`; không đổi `SE`/`SEM`, `SD`, `IQR` hoặc
`range` sang loại khác nếu paper không cung cấp phép chuyển đổi. Một target
approved phải có uncertainty số học và tên loại uncertainty rõ ràng.

Với schema hiện tại, trường `variance` lưu một độ rộng/spread số học đã được
paper báo cáo. Nếu nguồn báo hai cận thay vì một độ rộng, phải giữ target ở
trạng thái `pending` cho đến khi schema biểu diễn cận được review; không tự lấy
hiệu hai cận.

## Endpoint families

| Endpoint | Đơn vị | Trạng thái hiện tại | Quy tắc |
| --- | --- | --- | --- |
| `mean_planar_speed_mm_s` | `mm/s` | Calibration-eligible | Giá trị trung tâm phải là mean; không dùng median. |
| `median_planar_speed_mm_s` | `mm/s` | Calibration-eligible theo policy | Phải có numeric IQR hoặc range; simulation cũng phải xuất metric cùng tên trước khi chạy loss. |
| `distance_traveled_mm` | `mm` | Calibration-eligible theo policy | Là endpoint distance riêng, không đổi thành speed; notes phải ghi `statistic=mean` hoặc `statistic=median`. |
| `activity_time_s` | `s` | Validation-only | Không đổi thành speed hoặc pause fraction nếu chưa có assay implementation và transfer rule. |
| `climbing_score` | Theo assay | Validation-only | Chỉ được calibration khi climbing assay và metric được implement, kiểm thử và phê duyệt. |
| `DAM_activity` | Theo assay | Validation-only | Beam-break count/relative activity không phải planar walking speed. |

“Calibration-eligible theo policy” chỉ có nghĩa schema có thể biểu diễn target.
Audit readiness không xác nhận simulation đã sinh metric đó; bước execution
vẫn phải kiểm tra metric tồn tại trong artifact thật.

## Quy tắc assay transfer

Một target approved phải ghi trong `notes`:

```text
assay_transfer=allowed
```

Research lead chỉ được chọn `allowed` khi:

1. Endpoint paper và endpoint simulation đo cùng khái niệm vận động.
2. Đơn vị giống nhau hoặc có phép đổi đơn vị vật lý minh bạch.
3. Statistic trung tâm và uncertainty tương thích.
4. Thời lượng, cửa sổ quan sát và điều kiện assay đã được ghi nhận.
5. Không cần suy ra climbing, DAM count hoặc activity time thành speed.
6. Khác biệt tuổi, giới tính, genotype và môi trường được ghi trong limitation.

Nếu chỉ dùng để đối chiếu định tính, ghi `assay_transfer=validation_only`. Nếu
không thể so sánh, ghi `assay_transfer=not_comparable`. Hai trạng thái này
không được mở calibration gate.

## Unit of analysis và sample size

`sample_size` của target approved phải là một số nguyên dương và phải mô tả
đúng đơn vị thực sự được paper dùng để phân tích. `notes` phải ghi một trong:

```text
sample_unit=fly
sample_unit=animal
sample_unit=vial
sample_unit=independent_vial
sample_unit=recording
sample_unit=independent_experiment
```

Không nhân số ruồi mỗi vial với số vial nếu paper phân tích ở cấp vial. Không
đổi range như `3-10 vials` thành một số. Nếu endpoint không có một sample size
số học xác định thì giữ `pending`.

## Metadata và provenance bắt buộc

Target approved phải có đủ:

- paper ID, DOI hoặc PMID;
- gene/model và genotype;
- tuổi dạng số ngày và giới tính;
- assay, endpoint, value và unit;
- statistic/uncertainty type và uncertainty số học;
- sample size số học và sample unit;
- figure/table/supplementary provenance;
- reviewer thật và ngày review thật;
- `allocation=calibration` hoặc `allocation=holdout`;
- `assay_transfer=allowed`.

## Calibration và holdout

Một target chỉ có một allocation. Không dùng cùng endpoint, cùng paper và cùng
cohort cho cả calibration lẫn holdout. Holdout nên độc lập theo paper, cohort
hoặc assay; nếu khác assay thì transfer rule phải được phê duyệt riêng.

Ít nhất một target calibration và một target holdout đủ điều kiện mới cho phép
audit trả `READY_FOR_CALIBRATION`. Target validation-only không được tính vào
hai allocation này.

## Trạng thái hiện tại

Các candidate hiện có vẫn chưa đủ điều kiện approved. Riemensperger thiếu
numeric median spread; Pokrzywa thiếu exact SE và numeric unit of analysis;
Pozo cần xác nhận spread và simulation distance endpoint. Hwang/Godena chỉ
validation-only, còn Dumitrescu DAM không tương thích với speed.

Trạng thái kỳ vọng sau khi áp dụng policy là `WAITING_TARGET_DATA`.
