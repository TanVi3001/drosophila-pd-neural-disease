# Step 1: Khóa Healthy Neural Core

## Mục tiêu

Tạo một manifest tham chiếu bất biến tới neural source khỏe mạnh. Bước này không
chạy simulation, không bật disease layer, không calibration và không copy dữ liệu
nặng vào repository.

Healthy core là bản tham chiếu dùng cho mọi condition sau này. Disease branch phải
là cấu hình hoặc artifact riêng; không được ghi đè checkpoint, connectome hoặc file
healthy.

## Lệnh chạy

```powershell
py -3.12 scripts/lock_healthy_neural_core.py `
  --brain-root E:\Drosophila_Parkinson\phase-A-clean `
  --output results\neural_core_lock\healthy_neural_core_lock.json
```

Trạng thái thành công:

```text
HEALTHY_NEURAL_CORE_LOCKED
```

Trạng thái chờ hợp lệ:

```text
WAITING_BRAIN_DATA
WAITING_LICENSE_REVIEW
```

Không được đổi trạng thái chờ thành locked bằng cách sửa JSON thủ công.

## Kiểm tra được ghi nhận

- required brain source files;
- source manifest và SHA256;
- source repository commit nếu thư mục là Git checkout;
- project commit;
- code license và data-license status;
- disease layer/calibration/holdout đều tắt;
- không copy source bytes;
- chính sách cấm mutation healthy core.

`REVIEW_CC_BY_NC_4_0` chỉ ghi nhận license dữ liệu cần nhóm kiểm tra điều khoản và
citation. Nó không tự động có nghĩa là mọi cách phát hành artifact đều được phép.

## Điều kiện chuyển Step 2

Chỉ chuyển sang tạo disease branch khi:

1. manifest có `HEALTHY_NEURAL_CORE_LOCKED`;
2. source/checkpoint và checksum khớp;
3. license/citation đã được nhóm xác nhận;
4. healthy config vẫn trỏ tới core đó;
5. disease artifact được tạo ở thư mục riêng và có parent lock;
6. mọi neural perturbation có annotation, provenance và condition scope.

Step này chỉ khóa đầu vào. Nó không chứng minh neural network đã mô phỏng bệnh
Parkinson và không tạo disease metrics.
