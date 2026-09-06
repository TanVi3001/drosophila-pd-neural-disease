# Quy tắc quyết định mapping condition - Gate 20C

## Quy tắc không suy diễn

- Không lấy root ID từ tên gene.
- Không lấy toàn bộ neuron của một class để đại diện cho gene nếu paper/export không nói như vậy.
- Không biến mapping organism-level thành mapping gene-specific.
- Không dùng annotation local làm bằng chứng cho driver-to-root mapping nếu chưa có query/export và reviewer signoff.
- Không xóa hoặc ghi đè healthy core.

## Điều kiện để một condition được tính là approved

Tất cả điều kiện sau phải đúng:

1. Có ít nhất một root ID hoặc edge ID không phải placeholder.
2. Có cell type hoặc cell class, driver/anatomy scope và connectome version.
3. Có source URL, query string, query date, người xuất và SHA-256 của artifact.
4. Có `reviewer_2` và `review_date` hợp lệ trong `reviewer_signoff.json`.
5. `decision` là `APPROVED` hoặc `APPROVED_FOR_CLASS_LEVEL_EXPLORATORY` và mapping level khớp với phạm vi được phép.
6. YAML condition có target ID, provenance, burden curve và perturbation/full burden tương thích.
7. Audit gene-specific và audit disease mapping không còn blocker cho condition đó.

Thiếu một điều kiện thì condition bị block, dù đã có một file export.

## Ý nghĩa của 0/5

`0/5` nghĩa là hiện chưa có condition nào vượt toàn bộ cổng bằng chứng. Đây là kết quả hợp lệ. `5/5 reviewed` chỉ nói năm condition đã được đưa vào quy trình review, không có nghĩa năm condition đã được approve.

## Phạm vi theo condition

- `alpha_synuclein`: không coi pan-neuronal expression là root-ID set gene-specific.
- `pink1`: whole-animal phenotype cần quyết định model scope trước khi gán neuron/edge.
- `parkin`: TH-GAL4 có thể là class-level nếu export và reviewer xác nhận; không tự gọi gene-specific.
- `dj1`: behavioral evidence không đủ nếu không có intervention neural cụ thể.
- `lrrk2`: cần phạm vi motor-neuron/VNC tương thích; brain-only evidence không đủ.

## Các bước bị cấm ở Gate 20C

Gate này không chạy simulation, GPU, calibration, tuning, disease rollout, holdout validation và không tạo disease metrics. Những bước đó chỉ mở sau khi mapping gate và các gate khoa học liên quan đạt.
