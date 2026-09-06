# Chạy và lưu báo cáo tiết kiệm dung lượng

## Nguyên tắc

Rollout vẫn chạy với cùng physics, timestep, seed, QC và metrics. Chỉ thay đổi
retention policy sau khi kiểm tra xong: frame-level artifact được hash rồi xóa;
metrics, manifest, log, report và video đại diện được giữ lại.

Các file nặng thường gặp là `rollout.npz`, `rollout.csv`, `rollout.json`,
`viewer_pose.json` và `viewer_bundle`. Không được xóa bằng lệnh tổng quát ngoài
thư mục kết quả đã chọn.

## Audit trước khi dọn

Lệnh mặc định chỉ lập kế hoạch, không xóa gì:

```powershell
py -3.12 scripts/compact_results.py `
  --root results/healthy_baseline_reproducible
```

Đọc `storage_compaction_report.json`, kiểm tra candidate và số dung lượng dự
kiến thu hồi. `metrics`, `manifest`, `logs` và report không nằm trong allowlist.

## Dọn sau khi đã review

Giữ video đại diện và xóa raw/viewer artifact:

```powershell
py -3.12 scripts/compact_results.py `
  --root results/healthy_baseline_reproducible `
  --include-videos `
  --keep-glob "videos/*.mp4" `
  --apply
```

`--apply` là bắt buộc để xóa. Manifest JSON được ghi trước khi xóa và chứa
SHA256 của từng artifact bị xóa. Nếu chưa chắc, chỉ chạy dry-run.

## Gate 20

Gate 20 đã chạy mỗi rollout trong thư mục tạm và chỉ giữ metrics/QC, log,
manifest và video đại diện. Khi muốn tiếp tục từ các row `PASS`, dùng cơ chế
checkpoint/finalize thay vì chạy lại các seed đã đạt.

## Gate 19

Khi táº¡o baseline má»›i, dÃ¹ng `--discard-raw` Ä‘á»ƒ giá»›i háº¡n dung lÆ°á»£ng Ä‘á»‰nh:

```powershell
py -3.12 scripts/run_healthy_baseline_multiseed.py `
  --brain-root E:\path\to\phase-A-clean `
  --platform-root E:\path\to\drosophila-pd-flygym `
  --brain-python E:\path\to\python.exe `
  --discard-raw
```

Cá» nÃ y khÃ´ng thay Ä‘á»•i simulation. Sau khi seed Ä‘áº¡t numeric QC, metric contract vÃ 
physical QC, runner hash táº¥t cáº£ file raw, ghi `manifests/seed_NNN_raw_artifacts.json`,
rÃ²i má»›i xÃ³a thÆ° má»¥c seed. Metrics CSV/JSON, manifest tá»•ng, log vÃ  report váº«n Ä‘Æ°á»£c
giá»¯. Seed fail hoáº·c chÆ°a Ä‘áº¡t QC váº«n Ä‘Æ°á»£c giá»¯ raw Ä‘á»ƒ debug.

Healthy baseline có thể tổng hợp từ raw artifact hiện có bằng
`--aggregate-existing`, sau đó mới compact raw files. Không dùng playback video
để thay cho duration vật lý và không thay đổi metrics sau khi compact.

## Ranh giới khoa học

Compaction chỉ thay đổi lưu trữ cục bộ. Nó không sửa kết quả, không chạy lại
simulation, không tạo metrics và không thay đổi claim lock.
