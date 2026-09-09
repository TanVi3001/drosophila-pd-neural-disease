# Sửa lỗi tái lập giữa Windows và GitHub Actions

## Phạm vi

Tài liệu này ghi nhận một bản sửa hạ tầng tái lập cho checkout Linux của GitHub
Actions. Bản sửa không thay đổi raw metrics, checkpoint, mapping khoa học,
signoff, seed, lưới tham số hoặc kết luận Gate24E.

## Nguyên nhân

Một số artifact lịch sử được tạo trên Windows chứa CRLF hoặc kiểu xuống dòng
hỗn hợp. Các checksum đã khóa được tính trên byte gốc đó, trong khi checkout
Linux của Git tự động chuẩn hóa file thành LF. Vì vậy cùng một artifact có nội
dung đọc được giống nhau nhưng SHA256 khác nhau.

Ngoài ra, một số test cũ yêu cầu checkpoint và raw rollout nằm ngoài source
checkout. Những file này không được commit do kích thước và provenance; test
phải kiểm tra manifest đã khóa hoặc skip rõ ràng khi external artifact không
có mặt, thay vì làm hỏng bước collection.

## Điều chỉnh

- Khai báo các artifact byte-frozen với `-text` trong `.gitattributes` để
  checkout không tự đổi CRLF/LF.
- Đưa các summary JSON nhỏ đã được manifest Gate21 tham chiếu vào source tree;
  không đưa raw rollout hoặc checkpoint lớn vào Git.
- Cho runtime-adapter tests đọc frozen plan thay vì khởi động validation runtime
  ngoài repository trong lúc import module.
- Cho các test checkpoint phụ thuộc artifact ngoài repository skip có lý do khi
  artifact không được phân phối.
- Chuẩn hóa so sánh plan theo placeholder repository root để không phụ thuộc
  đường dẫn tuyệt đối của runner.
- Bảo toàn guard một lần của attempt_04 dựa trên storage history; directory
  raw có thể được lưu ngoài Git nhưng không được phép chạy lại.
- Làm mới Gate25-R2 để ghi nhận thay đổi vận chuyển artifact đa nền tảng.

## Kết quả bảo toàn

- Gate24E scientific result vẫn là `NEGATIVE_VALIDATION_RESULT`.
- Final evidence freeze, virtual freeze và raw-tree metadata không bị thay đổi.
- Không chạy GPU, simulation, calibration hoặc scientific batch trong bản sửa.
- Bản sửa chỉ làm cho clean checkout tái lập đúng các artifact và kiểm thử đã
  được khóa.

## Kiểm tra bắt buộc

Clean checkout phải chạy được compileall, pytest, Gate25-R2 verify-only và
`git diff --check`. Các checkpoint/raw rollout không có trong source checkout
không được biến thành kết quả giả; chúng chỉ được kiểm tra khi artifact tương
ứng thực sự tồn tại.
