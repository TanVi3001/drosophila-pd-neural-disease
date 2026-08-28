# Chạy GPU

Môi trường mục tiêu là Python 3.12 và PyTorch/CUDA tương thích với GPU. Với
GPU 6 GB, chạy một process mỗi lần, không chạy song song nhiều seed và không
lưu tensor dense toàn mạng.

Quy tắc vận hành:

1. Kiểm tra driver và CUDA.
2. Kiểm tra checkpoint/connectome có checksum.
3. Chạy healthy baseline trước.
4. Reset về checkpoint healthy trước mỗi condition.
5. Không ghi đè checkpoint healthy.
6. Ghi video sau rollout nếu việc render đồng thời gây thiếu VRAM.
7. Ghi lại peak VRAM, thời gian, seed và cấu hình.

Hebbian plasticity nếu được bật phải có protocol riêng. Nếu weight bị thay đổi
và lưu chung giữa các run, comparison sẽ bị nhiễu bởi lịch sử chạy.
