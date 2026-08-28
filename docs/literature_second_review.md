# Second-pass audit literature và mapping

Ngày audit: 2026-08-28.

## Phạm vi

Audit này kiểm tra lại provenance, full text, supplementary, vị trí figure/table,
uncertainty, assay transfer và phạm vi mapping neuron của 14 candidate records trong
`datasets/literature_phenotypes/phenotype_records.csv`.

Đây là kiểm tra tài liệu có thể tái lập từ artifact đã lưu và nguồn primary đã đăng ký.
Nó không thay thế reviewer độc lập của nhóm nghiên cứu. Vì vậy không record nào được
đổi sang `approved`, `calibration` hoặc `holdout` trong audit này.

## Kết quả tổng quát

- 14/14 record có paper ID, DOI/PMID, source URL, figure/table reference và sample-size field.
- 14/14 record vẫn ở hàng đợi review; không có numeric calibration target được phê duyệt.
- Các record alpha-synuclein có giá trị mean velocity trong phần kết quả, nhưng uncertainty dạng SE chưa có số cụ thể.
- Các record PINK1 có giá trị trung tâm và độ phân tán được báo cáo, nhưng caption mô tả IQR/extrema còn prose dùng ký hiệu plus/minus; không được gán spread đó là SD.
- Parkin là DAM beam-break activity, không phải walking speed; không được quy đổi tự động.
- DJ-1 và LRRK2 có thông tin figure/uncertainty convention nhưng tâm số đọc từ hình chưa được ghi vào bảng vì chưa có phép đọc độc lập được lưu.

## Root-ID mapping

Mapping hiện có cho dopamine deficiency là mapping theo cell class gồm 342 root IDs,
chỉ dùng exploratory. Nó không phải gene-specific disease mapping.

Các gene/model còn lại chưa có mapping gene-specific đã được review:

- alpha-synuclein: pan-neuronal driver, chưa có export root-ID được duyệt.
- parkin: TH-GAL4 xác định cell class, chưa có root-ID set được duyệt.
- PINK1: mutation ở mức model, không tự suy ra neuron subset.
- DJ-1: paper không cung cấp can thiệp cell-specific để map root IDs.
- LRRK2: driver nhắm motor neurons; catalog connectome hiện tại không đủ phạm vi brain/VNC để tự map.

Chi tiết nằm trong `root_id_mapping_audit.csv`. Không thêm root ID mới vào
`annotations/neuron_annotations.csv` nếu chưa có provenance độc lập và chữ ký reviewer.

## Điều kiện để nhóm duyệt một record

Reviewer thứ hai cần ghi identity và ngày review, sau đó xác nhận từng mục:

1. genotype, tuổi, giới tính và đơn vị đo đúng với paper;
2. figure/table/supplementary đã được đọc độc lập;
3. statistic type và uncertainty chính xác, không suy ra từ chiều cao cột;
4. assay có thể chuyển sang endpoint FlyGym hay phải để validation-only;
5. root-ID mapping có nguồn độc lập, hoặc đánh dấu không áp dụng;
6. target được phân vào calibration hoặc holdout, không đồng thời cả hai.

Chỉ sau khi đủ các mục trên mới có thể cập nhật trạng thái trong dataset và chạy
`scripts/audit_calibration_targets.py`. Trạng thái hiện tại vẫn là
`WAITING_TARGET_DATA`.

## Ranh giới khoa học

Các artifact này phục vụ chuẩn bị hiệu chuẩn cho computational locomotion model.
Chúng không chứng minh mô hình Parkinson sinh học, không phải chẩn đoán, không phải
dự đoán lâm sàng và không phải bằng chứng đáp ứng thuốc.
