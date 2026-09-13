# Kaggle demo: alpha-synuclein/dopamine brain-body rollout

Notebook demo: `notebooks/kaggle_alpha_syn_dopamine_demo.ipynb`.

Demo này chỉ kiểm tra môi trường Kaggle và chạy tối đa **một rollout 100 bước** khi người dùng chủ động bật `RUN_DEMO = True`. Nó không chạy `scripts/run_alpha_syn_dopamine.py --execute`, không đại diện cho scientific batch 15 job và không tạo kết luận khoa học.

## 1. Chuẩn bị GitHub và Kaggle Dataset

1. Push branch chứa hai commit `d061e34` và `aa309c3` lên GitHub. Notebook mặc định dùng branch `review/gate-20e-promote-parkin-class-level-signoff`.
2. Tạo một Kaggle Dataset private, ví dụ `drosophila-pd-fly-brain-v1`, bằng thư mục `external/fly-brain/`.
3. Dataset phải giữ nguyên các file brain source và data, đặc biệt:
   - `brain_body_bridge.py`
   - `code/run_pytorch.py`
   - `code/benchmark.py`
   - `data/2025_Completeness_783.csv`
   - `data/2025_Connectivity_783.parquet`
   - `data/plastic_weights.pt`
   - `data/weight_coo.pkl` và `data/weight_csr.pkl` nếu muốn tránh bước chuyển đổi lại.
4. Tạo Kaggle Notebook, bật `Settings → Accelerator → GPU`, attach Dataset ở bước Add Input, rồi upload notebook demo.

Nếu slug Dataset khác `drosophila-pd-fly-brain-v1`, sửa biến `BRAIN_DATASET_SLUG` trong cell đầu tiên.

## 2. Cách chạy demo

Chạy các cell theo thứ tự. Cell cuối có `RUN_DEMO = False` mặc định để không chạy mô phỏng ngoài ý muốn.

Khi muốn chạy demo một job:

1. Đổi `RUN_DEMO = True`.
2. Giữ `DEMO_STEPS = 100` cho lần đầu.
3. Chạy lại cell demo.
4. Kiểm tra `status.json`, `manifest.json` và metrics trong `/kaggle/working/kaggle_alpha_syn_dopamine_demo/`.

Không đổi `DEMO_STEPS` thành 5,000 trong notebook demo và không gọi `--execute`. Scientific batch mới trên cloud phải có execution manifest/authorization riêng sau khi freeze môi trường cloud.

## 3. Lưu ý về thời gian và disk

- Copy Dataset từ `/kaggle/input` sang `/kaggle/working` để brain data chạy trên local disk của Kaggle, không đọc trực tiếp từ storage mạng.
- Không bật video và không upload toàn bộ viewer bundle về máy cá nhân.
- Demo 100 bước chỉ nhằm kiểm tra tương thích CUDA/FlyGym/MuJoCo và đường dẫn; không dùng output demo để phân tích hoặc viết claim.
- Sau khi xem xong, có thể xóa thư mục demo trong Kaggle session; không ảnh hưởng dữ liệu Dataset.

## 4. Ranh giới reproducibility

Notebook ghi lại project ref, FlyGym ref, Python version, GPU name, brain checkpoint SHA256 và đường dẫn output. Dataset brain phải được version hóa trên Kaggle; không sửa file trong Dataset sau khi attach mà không tạo version mới.
