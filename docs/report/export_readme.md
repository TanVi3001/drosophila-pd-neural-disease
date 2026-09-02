# Gói xuất báo cáo Gate 17B

Gói này xuất `docs/report/final_vietnamese_report.md` thành hai định dạng để
nhóm nghiên cứu dễ đọc và gửi cho reviewer:

- `experiments/gate_17b_report_export/results/final_vietnamese_report.docx`
- `experiments/gate_17b_report_export/results/final_vietnamese_report.pdf`

## Cách chạy

Trong môi trường Python 3.12 của project, cài các gói xuất tài liệu:

```powershell
.venv\Scripts\python.exe -m pip install python-docx reportlab pypdf pymupdf
.venv\Scripts\python.exe scripts/export_final_report_package.py
```

Script đọc đúng báo cáo Markdown đã được merge ở Gate 17A, không chạy GPU,
simulation, calibration hoặc tuning. Mỗi lần chạy sẽ cập nhật summary và
manifest của Gate 17B, trong đó có SHA256 của file nguồn và file xuất.

## Artifact và trạng thái

- `results/report_export_summary.json`: trạng thái xuất, số trang PDF, kiểm tra
  nội dung và trạng thái visual QA.
- `manifests/report_export_manifest.json`: provenance, commit, phiên bản Python,
  đường dẫn nguồn, file sinh ra và checksum.
- `results/final_vietnamese_report.docx`: bản Word có heading, danh sách và
  bảng có thể chỉnh sửa.
- `results/final_vietnamese_report.pdf`: bản PDF cố định để đọc và gửi review.

Nếu máy có LibreOffice/`soffice`, script có thể hoàn tất render DOCX và trạng
thái là `REPORT_EXPORT_READY`. Nếu không có, DOCX/PDF vẫn được sinh nhưng
trạng thái là `REPORT_EXPORT_PARTIAL` và manifest ghi rõ lý do visual QA chưa
render được DOCX.

## Ranh giới khoa học

Đây chỉ là thao tác đóng gói và xuất báo cáo từ artifact đã có. Gate 17B
không tạo kết quả khoa học mới và không thay đổi claim lock. Báo cáo vẫn phải
được đọc theo giới hạn hiện hành: computational locomotion proxy ở mức
organism-level, không phải biological Parkinson validation, gene-specific
validation, clinical validation, drug validation hay therapeutic validation.
