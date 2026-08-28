# Paper Review Workspace

Thư mục này chứa kết quả audit nguồn tự động cho sáu paper và mười bốn candidate phenotype đã có trong `datasets/literature_phenotypes/`.

- `paper_analysis_vi.csv`: một dòng cho mỗi `record_id`; giữ nguyên assay, statistic, uncertainty và trạng thái review.
- `paper_summary.md`: diễn giải tiếng Việt theo từng paper và giới hạn chuyển đổi sang FlyGym.
- `paper_information.json`: metadata bibliographic và trạng thái nguồn.
- `paper_pdf_manifest.csv`: hash và provenance của PDF gốc hoặc fallback toàn văn.

PDF và supplementary được tải vào `temporary/` để review cục bộ và không được commit vì `.gitignore` loại trừ dữ liệu tạm và artifact lớn.

## Quy tắc trạng thái

`AUTOMATED_SOURCE_AUDIT` chỉ có nghĩa là nguồn đã được đọc và đối chiếu tự động. Nó không thay thế reviewer thứ hai. Mọi record hiện giữ `PENDING_HUMAN_SIGNOFF`; không được chuyển sang calibration hoặc holdout nếu chưa có reviewer, ngày review, uncertainty và quyết định assay transfer có provenance.
