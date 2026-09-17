# Bản đồ hợp nhất nghiên cứu connectome

Ngày rà soát: 2026-09-15

Registry máy đọc được nằm ở
[`configs/connectome_source_registry.json`](../../configs/connectome_source_registry.json).
Kiểm tra registry bằng:

```powershell
python scripts/validate_connectome_registry.py --workspace-root "D:\research\New folder\drosophila-pd-neural" --verify
```

`--verify` checks both the pinned git HEAD of every cloned repository and the
SHA-256 of every artifact that has a checksum in the manifest.

## Kết luận kiến trúc

Không nên “gộp” tất cả repo thành một neural model duy nhất. Các repo hiện có
đang giải quyết bốn lớp khác nhau:

```text
MaleCNS v1.0 / FlyWire 783
        |
        +-- 2025malecns + flywire_annotations  -> derived annotations, flow, dimorphism
        +-- neuprint-python + malecns            -> query and dataset access
        +-- navis + fafbseg + coconatfly         -> morphology and cross-dataset analysis
        +-- visualpathways                       -> visual-pathway hypothesis generation
        +-- synister_malecns                     -> EM-based transmitter prediction
        +-- Drosophila_brain_model + fly.ai     -> independent LIF/sandbox references
        |
        v
drosophila-pd-neural: provenance -> mapping audit -> checkpoint preparation
        |
        v
drosophila-pd-flygym: real neural consumer required before rollout
```

`drosophila-pd-flygym` vẫn là source of truth cho controller, action hook,
MuJoCo và locomotion metrics. Connectome repositories không được import ngầm
vào runtime đó.

## Vai trò của từng repo

| Nhóm | Repo | Dùng để làm gì | Không được suy ra |
|---|---|---|---|
| Nguồn/dẫn xuất | `2025malecns` | MaleCNS flow, male–female edges, mapping, communities, QC | Không phải neural checkpoint |
| Nguồn/dẫn xuất | `flywire_annotations_3.1.0` | Female FlyWire v783 annotations | Không phải annotation MaleCNS trực tiếp |
| Truy vấn | `neuprint-python`, `malecns` | Lấy metadata/partners/mesh từ MaleCNS | Không tự chứng minh gene-specific target |
| Hình thái | `navis`, `fafbseg-py` | Skeleton, mesh, transform, FlyWire access | Không thay thế provenance của mapping |
| So sánh | `coconatfly` | Comparative connectomics | Không phải runtime |
| Pathway | `visualpathways` | Phân tích visual pathways | Không phải bằng chứng PD |
| Phân tử | `synister_malecns` | Dự đoán neurotransmitter từ EM | Dự đoán không phải đo sinh lý |
| Mô hình độc lập | `Drosophila_brain_model`, `fly.ai` | LIF/reservoir reference và sandbox | Không thay thế FlyGym contract |

## Promotion gates

Mọi artifact phải giữ `source_dataset`, `id_namespace`, `source_repo`, commit và
checksum. Các namespace hiện tại tối thiểu là:

- `flywire_root_id` cho FlyWire 783;
- `male_cns_body_id` cho MaleCNS v1.0;
- `mixed_male_body_id_and_flywire_root_id` cho bảng cross-match.

Một cross-match group chỉ cho phép audit hoặc chọn candidate. Để tạo checkpoint
cần mapping đã review, target đã được duyệt và checksum. Để chạy rollout cần
thêm neural consumer thật sự đọc checkpoint; hiện tại điều kiện này chưa đạt.

Các trạng thái khoa học vì vậy là:

1. `AUDIT_ONLY`: kiểm tra schema, QC, provenance, mapping và figure.
2. `CROSSMATCH_AUDIT_ONLY`: dùng để so sánh male/female, chưa gán ID.
3. `CHECKPOINT_ELIGIBLE`: đủ provenance và mapping cho bước chuẩn bị checkpoint.
4. `ROLLOUT_ELIGIBLE`: chỉ khi platform có consumer và test end-to-end.

## Phân tích nên làm tiếp theo

1. Chọn một target circuit nhỏ, ví dụ descending neurons liên quan vận động,
   thay vì tải toàn bộ synapse table.
2. Dùng `neuprint-python` read-only để lấy metadata và upstream/downstream
   partners cho target đó; lưu response, query, dataset version và checksum.
3. Đối chiếu target với `dnan_cluster_function` và `mcns_fw_edge_comp` mà vẫn
   giữ hai namespace riêng.
4. Dùng `navis` để kiểm tra skeleton/mesh và tạo audit figure.
5. Chỉ sau khi mapping được reviewer duyệt mới viết adapter checkpoint.
6. Giữ output là computational evidence; không gọi là biological Parkinson
   validation nếu chưa có assay bridge và neural runtime consumer.

## Các blocker còn lại

- Chưa có NeuPrint credential trong workspace nên chưa chạy live query.
- Chưa có R/Rscript để chạy `malecns` và `coconatfly`.
- `synister_malecns` cần Linux/pixi, EM volume, ground truth và checkpoint.
- `visualpathways` có artifact/data dependency lớn, không phù hợp nhúng vào core.
- Runtime FlyGym hiện chưa tiêu thụ edge checkpoint connectome.
- Các mapping gene-specific trong project hiện vẫn cần review riêng; không được
  suy từ cell type hoặc cross-match group.
