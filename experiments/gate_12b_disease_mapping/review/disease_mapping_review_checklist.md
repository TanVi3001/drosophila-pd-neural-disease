# Gate 12B — Checklist review disease mapping

Checklist này dành cho reviewer xác nhận trước khi condition được chuyển sang `RUN_READY`.
Không đánh dấu đạt chỉ vì đã có tên gene hoặc driver. Mọi target phải có nguồn, phạm vi và phiên bản rõ ràng.

## Danh tính reviewer

- [ ] Tên reviewer chính
- [ ] Vai trò reviewer
- [ ] Ngày review theo định dạng `YYYY-MM-DD`
- [ ] Reviewer thứ hai (nếu quy trình yêu cầu)
- [ ] Ngày review thứ hai

## Mapping neural

- [ ] Nguồn mapping root ID được ghi rõ
- [ ] Phiên bản FlyWire/connectome được ghi rõ
- [ ] Danh sách `target_neurons` đã được kiểm tra tồn tại
- [ ] Danh sách `target_edges` đã được kiểm tra tồn tại và đúng chiều
- [ ] `target_classes` được tách khỏi root-ID mapping cá thể
- [ ] Driver/expression scope được ghi rõ
- [ ] Mapping không được suy ra chỉ từ tên gene

## Burden và condition

- [ ] `burden_curve` có mốc tuổi và đơn vị rõ ràng
- [ ] `full_burden` có định nghĩa cho từng tham số
- [ ] Các giá trị burden có provenance từ nguồn hoặc policy đã duyệt
- [ ] Không dùng Chen/Pozo để tune condition trong Gate 12
- [ ] Scope được phân loại: `gene_specific`, `class_level`, `organism_level` hoặc `not_ready`

## Runtime và provenance

- [ ] Checkpoint source được xác định
- [ ] Checkpoint tương thích với runtime Gate 11
- [ ] SHA-256 checkpoint được ghi nếu artifact có sẵn
- [ ] Literature source được ghi
- [ ] Mapping source được ghi
- [ ] Manifest input/output được cập nhật

## Quyết định chạy

- [ ] Tất cả field bắt buộc đã có
- [ ] `run_status=RUN_READY` chỉ khi target, burden, mapping và runtime đều hợp lệ
- [ ] Nếu thiếu bất kỳ field nào, giữ `run_status=BLOCKED`
- [ ] `blocked_reason` được ghi cụ thể
- [ ] Đã xác nhận Gate 12B không chạy simulation, calibration hoặc holdout validation
