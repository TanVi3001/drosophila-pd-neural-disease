# Gate 24E-M1: nguyên nhân lỗi bộ nhớ và profile xuất an toàn

## Phạm vi

Gate 24E-M1 chỉ sửa cách ghi và hậu xử lý artifact sau `simulation.step()` cuối
cùng. Không chạy lại GPU, không chạy attempt 03, không mở holdout, không đổi
Parkin transform, mapping, checkpoint, seed, physics, CPG, controller hay luật
quyết định.

## Bằng chứng từ platform đóng băng

Platform gốc được kiểm tra tại commit
`3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06` trong worktree sạch.

1. `src/drosophila_pd/flygym_adapter/export.py` gọi
   `rollout.to_dict()` trước khi ghi JSON. Đây là đường tạo toàn bộ document
   frame trong Python rồi mới gọi `json.dumps(...)`.
2. `src/drosophila_pd/flygym_adapter/types.py` định nghĩa
   `RolloutData.to_dict()` bằng biểu thức tương đương
   `"frames": [frame.to_dict() for frame in self.frames]`. Vì vậy toàn bộ
   frame dictionary và toàn bộ giá trị số đã bị materialize thêm trong RAM.
3. `src/drosophila_pd/analysis/rollout_analysis.py` khi thấy `rollout.json`
   dùng `json.loads(json_path.read_text(...))`, sau đó còn tạo list `frames`.
   Một writer JSON streaming đơn độc vì vậy không đủ để sửa downstream.
4. `src/drosophila_pd/viewer_export/pose_exporter.py` cũng đọc toàn bộ
   `rollout.json`, lấy frame list và `build_viewer_pose()` tạo document
   `frames` đầy đủ trước khi serialize. Đây là rủi ro bộ nhớ thứ hai.
5. Exporter legacy dùng các list giá trị và `np.stack(...)` cho từng channel,
   nên có thể tạo thêm bản sao lớn trong khi `RolloutData.frames` vẫn còn ở
   trong bộ nhớ.

Attempt 02 đã hoàn thành 100.000 bước vật lý rồi thất bại tại bước export
`rollout.json` với `MemoryError`. Vì vậy số đo dung lượng của attempt 02 được
giữ là không hợp lệ cho capacity estimation.

## Thay đổi M1

Worktree platform mới được tạo từ đúng commit gốc, không sửa worktree đóng
băng:

- Branch: `runtime/gate24e-memory-safe-export`
- Commit: `655e854544e3d814dfe422883ff0de66b619d6c1`
- Profile: `GATE24E_MEMORY_SAFE`
- Default legacy profile: `LEGACY`

Profile mới:

- ghi từng channel vào `.npy` memmap;
- ghi `rollout.npz` bằng ZIP streaming;
- không gọi `RolloutData.to_dict()` hoặc `ObservationFrame.to_dict()`;
- không tạo full-frame `rollout.json`;
- phân tích scalar trực tiếp từ `rollout.npz` để lấy
  `median_planar_speed_mm_s` và `distance_traveled_mm`;
- bỏ qua viewer/pose/video và biomarker hậu xử lý tùy chọn trong profile
  chính, với trạng thái được ghi rõ;
- giải phóng frame sau khi NPZ đã được ghi thành công.

Vòng lặp mô phỏng vẫn theo thứ tự brain step, decoder/bridge, controller,
`apply_locomotion_action`, `simulation.step()` và `recorder.record()` như
trước. Profile chỉ được áp dụng sau bước vật lý cuối cùng.

## Regression và ranh giới khoa học

Test semantic equivalence so sánh tất cả channel NPZ giữa exporter legacy và
profile mới trên rollout nhỏ. Test memory regression xác nhận không gọi
serializer frame và theo dõi peak Python memory trên fixture tổng hợp.

Kết quả M1 không phải kết quả khoa học mới. Nó chỉ cho phép một lần review
provenance vận hành tiếp theo. Platform commit mới không được tự động thay
model-freeze commit cũ và không làm mất human signoff Gate 24D.

Trạng thái sau M1:

```text
MEMORY_SAFE_EXPORT_IMPLEMENTED
WAITING_GATE24E_RUNTIME_PROVENANCE_AMENDMENT
attempt_03 executed: NO
GPU simulation: NO
scientific jobs: 0
holdout: SEALED
```
