# Tích hợp nguồn dataset có kiểm soát

## Kết luận kiểm tra

Báo cáo nguồn dữ liệu được cung cấp là một bản kê khai, không phải gói dataset.
Workspace hiện có đủ connectome FlyWire v783, annotation, completeness và
checkpoint từ nguồn brain bên ngoài. Các file này khớp kích thước và SHA256 đã
ghim trong `data/SOURCE_PROVENANCE.md`.

Những nhóm dữ liệu sau chưa được tìm thấy nên chưa được tích hợp:

- `experimental_locomotion_db.json`;
- `sez_neurons.pickle`;
- checkpoint cá thể `plastic_weights_fly0.pt` và `plastic_weights_fly1.pt`;
- bốn ảnh ommatidia;
- 28 file `bridge_scales`;
- raw multi-seed, held-out validation và Sobol evaluations được mô tả.

Không được tái tạo các file thiếu từ con số ghi trong báo cáo. Làm như vậy sẽ
biến một mô tả thứ cấp thành dữ liệu khoa học giả.

## Dữ liệu đã đưa vào luồng chạy

Catalog `data/source_catalog.json` ghi nguồn, commit, license, kích thước, SHA256
và shape đã kiểm tra. Dữ liệu lớn không được commit vào Git. Có thể tái tạo đầu
vào bằng:

```powershell
python scripts/fetch_brain_source.py --output external/fly-brain
python scripts/check_neural_inputs.py `
  --brain-root external/fly-brain `
  --output results/neural_input_status.json
```

Nếu `source_manifest.json` có mặt, checker đọc toàn bộ file bắt buộc và đối
chiếu kích thước cùng SHA256. File đổi nội dung hoặc tải thiếu trả trạng thái
`INVALID_BRAIN_DATA`; simulation không nên tiếp tục.

## Kiểm tra shape thực tế

| Thành phần | Kết quả |
| --- | ---: |
| Neuron trong completeness | 138.639 |
| Dòng `Completed=True` | 138.639 |
| Dòng annotation | 139.244 |
| Cột annotation | 31 |
| Cạnh connectome | 15.091.983 |

Các con số này mô tả shape file, không xác nhận tính đúng sinh học của từng
mapping. Báo cáo ghi 284 neuron dopaminergic, trong khi bộ lọc hiện tại của
project chọn 342 root ID thuộc các cell type PAM/PPL/PPM có `top_nt=dopamine`.
Hai con số dùng tiêu chí khác nhau và không được xem là tương đương.

## Audit y văn

Metadata nguồn được ghi trong
`research/dataset_intake/literature_source_review.csv`. Audit phát hiện:

- DOI của Coulom 2004 trong báo cáo bị sai; DOI đúng là
  `10.1523/JNEUROSCI.2993-04.2004`.
- DOI của Riemensperger 2013 trong báo cáo bị sai; DOI đúng là
  `10.1016/j.celrep.2013.10.032`.
- DOI `10.1016/j.cub.2025.12.015` không phải paper Drosophila; nó trỏ tới bài
  bình luận về cạnh tranh vi khuẩn, nên nguồn `Liessem_2026` bị loại.
- Các chuỗi vận tốc, lực, dopamine, dose-response và aging chưa có trích xuất
  cấp từng figure/table cùng uncertainty, nên không được nhập vào calibration.

## Cách project sử dụng dataset

1. Connectome và checkpoint đã xác minh cung cấp đầu vào cho brain runtime.
2. Annotation đã review xác định neuron mục tiêu; không dùng vị trí tensor để
   suy ra cell type.
3. `prepare_neural_checkpoint.py` áp perturbation lên cạnh connectome và sinh
   checkpoint mới có manifest/checksum.
4. Literature chỉ được dùng làm calibration/holdout sau review thủ công về
   assay, metric, tuổi, giới tính, sample size, statistic và uncertainty.
5. Rollout FlyGym thật mới được đưa sang analysis và so sánh.

Metadata có thể clone cùng repository nằm ở `datasets/`. Bản báo cáo nguồn được
lưu nguyên byte trong `datasets/source_intake/`, còn paper registry, 14 phenotype
candidate và trạng thái gene-condition nằm trong `datasets/literature_phenotypes/`.
Các file lớn vẫn được lấy theo commit/checksum từ catalog; không có checkpoint
hay connectome nhị phân nào được đưa vào Git.

## Ranh giới khoa học

Tích hợp này tạo một đầu vào connectome có provenance cho perturbation neural
tính toán. Nó chưa xác nhận mô hình Parkinson sinh học, chưa chứng minh quan hệ
gene-to-neuron cụ thể và không hỗ trợ chẩn đoán, dự đoán lâm sàng hay đánh giá
thuốc.
