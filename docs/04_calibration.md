# Calibration và holdout

Calibration chỉ được chạy khi target literature có:

- paper và DOI/PMID;
- genotype/model;
- tuổi và giới tính nếu có;
- assay và đơn vị;
- metric định lượng;
- variance và sample size nếu paper cung cấp;
- figure/table/page;
- trạng thái review đã được duyệt.

Không dùng cùng target cho calibration và holdout. Mỗi kết quả phải lưu seed,
commit nền tảng, condition config, annotation checksum, connectome checksum và
checkpoint checksum.

Loss hỗ trợ trong package gồm RMSE, MAE, cosine và Huber. Đây là công cụ so
sánh số học, không phải thước đo “mức độ bệnh”.

Kết quả phải báo cáo cả:

```text
Disease_simulation - Healthy_simulation
Disease_literature  - Healthy_literature
```

và kiểm tra hướng thay đổi, độ lớn, uncertainty, seed variability và holdout.
