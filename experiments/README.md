# Thiết kế thí nghiệm

Mỗi thí nghiệm phải có một healthy checkpoint cố định và chỉ thay đổi một
condition neural đã được khai báo. Giữ nguyên seed, body, terrain, timestep,
stimulus và duration khi so sánh healthy với disease.

Các thí nghiệm bắt buộc gồm:

- healthy baseline;
- disease condition;
- ablation theo từng thành phần perturbation;
- nhiều seed;
- holdout theo paper hoặc target.

Chưa có target/annotation thì trạng thái là `WAITING_TARGET_DATA`, không chạy
simulation và không sinh figure hay kết luận.
