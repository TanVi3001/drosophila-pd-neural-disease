# Dữ liệu ngoài Git

Các file connectome, checkpoint và dataset thật không được commit trực tiếp
trong repository này. Hãy đặt chúng ở các thư mục bị ignore và ghi vào manifest:

- đường dẫn artifact;
- nguồn và license;
- phiên bản;
- SHA256;
- ngày tiếp nhận;
- người review.

Không dùng file chưa có provenance để calibration hoặc kết luận.

Catalog nguồn đã kiểm tra nằm ở `source_catalog.json`. Kết quả audit báo cáo
dataset ngày 28-08-2026 nằm trong `research/dataset_intake/`. Các artifact chỉ
được mô tả nhưng chưa cung cấp file gốc không được xem là dataset đã tích hợp.

Các metadata nhỏ được nhóm cùng review nằm trong [`../datasets/`](../datasets/).
Thư mục đó chứa bản báo cáo nguồn có checksum, paper registry và phenotype
candidate; nó không chứa connectome/checkpoint nhị phân và không tự cấp quyền
calibration cho bất kỳ record nào.
