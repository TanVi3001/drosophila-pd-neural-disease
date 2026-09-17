# Báo cáo cài đặt và đánh giá các repo connectome mới

Ngày rà soát: 2026-09-15

Phạm vi: drosophila-pd-neural, drosophila-pd-neural-disease,
drosophila-pd-flygym và các nguồn/repo connectome được đề xuất.

## 1. Kết luận điều hành

Đợt đánh giá đã hoàn tất ở mức an toàn cho repository hiện tại:

- Đã clone 10 repo vào D:\research\New folder\external.
- Đã cài neuprint-python, navis và fafbseg trong venv phân tích Python 3.12
  riêng; pip check đạt.
- Đã cài FlyGym 2.1.0 và MuJoCo 3.9.0 trong venv runtime riêng; paired
  action-level proxy burden chạy thật đạt PASS ở smoke test 10 bước.
- Đã cài flybrain trong sandbox riêng; CLI info chạy được và dừng đúng ở
  trạng thái thiếu dữ liệu, không tự tải connectome.
- Đã kiểm tra artifact dữ liệu 2025malecns và flywire_annotations v3.1.0
  bằng pandas/pyarrow/openpyxl, gồm schema, số dòng, duplicate ID, mapping
  và checksum.
- Không thêm dependency connectome vào runtime core của FlyGym hoặc neural
  extension.

Kết luận kỹ thuật: cải thiện lớn nhất nằm ở lớp annotation, mapping,
connectivity audit, morphology và provenance. Chưa có cải thiện ở neural
runtime hoặc bằng chứng sinh học Parkinson, vì artifact mới chưa được tiêu
thụ bởi runner neural tương thích với FlyGym.

## 2. Baseline hiện tại

| Hạng mục | Kết quả đã kiểm tra | Diễn giải |
|---|---:|---|
| drosophila-pd-neural | 170 passed | Regression suite đạt; platform contract READY. |
| drosophila-pd-neural-disease | 747 passed, 8 skipped, 2 failed | Hai failure hiện hữu: tracking hook kỳ vọng không khớp platform local; trạng thái human signoff Gate28B đã bị promote. |
| drosophila-pd-flygym | 515 passed, 2 skipped, 2 failed | Hai failure ở rollout rất ngắn do heading_rad toàn NaN trong turning metric. |
| Proxy action-level | PASS | Burden 0.5, seed 0, 10 steps; baseline và perturbed finite, 42 position actuators và 6 adhesion actuators. |
| Annotation hiện tại | 360 neuron ID, 39 cell type | Chưa có edge-list MaleCNS thật trong repo; source catalog chỉ mô tả external artifact. |

Các con số rollout smoke chỉ là kiểm tra phần mềm và hợp đồng action, không
phải kết quả sinh học hay validation Parkinson.

### Failure baseline cần tách khỏi connectome

Venv cũ của neural extension không có matplotlib, FlyGym và MuJoCo, nên
launcher proxy trả WAITING_RUNTIME. Venv runtime mới đã khắc phục thiếu
dependency đó. Full platform suite vẫn lộ lỗi heading_rad không finite trong:

- tests/test_healthy_baseline.py::test_healthy_baseline_integration_with_real_flygym_if_available;
- tests/test_perturbation_experiment.py::test_paired_perturbation_integration_with_real_flygym_if_available.

Không sửa hai failure này trong vòng đánh giá repo mới để tránh trộn thay đổi
platform với thay đổi provenance.

## 3. Môi trường đã cài

### 3.1 Venv phân tích connectome

Đường dẫn: D:\research\New folder\.venvs\connectome-analysis-312
Python: 3.12.10
Kết quả: pip check = No broken requirements found.

| Package | Version |
|---|---:|
| neuprint-python | 0.6.3 |
| navis từ PyPI | 1.12.0 |
| fafbseg | 3.2.2 |
| caveclient | 8.2.1 |
| cloud-volume | 12.14.4 |
| numpy | 2.5.3 |
| pandas | 2.3.3 |
| pyarrow | 25.0.1 |
| openpyxl | 3.1.5 |

Smoke test đạt:

- import cả ba package Python;
- tạo navis.TreeNeuron mẫu 4 node, cable length 3.414213562373095;
- tạo fafbseg.flywire.NeuronCriteria offline;
- neuprint.Client với dataset male-cns:v1.0 chặn đúng bằng RuntimeError
  khi không có token.

### 3.2 Venv runtime FlyGym

Đường dẫn: D:\research\New folder\.venvs\flygym-runtime-312

Đã cài editable platform và neural extension cùng:

- flygym==2.1.0;
- mujoco==3.9.0;
- matplotlib, pytest và dependency platform.

drosophila-pd-neural chạy lại toàn bộ suite trong venv này: 170 passed.

### 3.3 Sandbox flybrain

Đường dẫn: D:\research\New folder\.venvs\flybrain-sandbox-312

Đã cài editable repo fly.ai, package flybrain==0.1.0. Lệnh flybrain
--version và flybrain info đạt. Brain weights không có local; chưa chạy
FlyBrain() vì lần đầu sẽ tải khoảng 260 MB dữ liệu ngoài repo.

## 4. Kiểm tra dữ liệu mới và cải thiện định lượng

### 4.1 flyconnectome/2025malecns

Repo đã clone ở commit:

67767d2233657983993ff6c2be48e836a935863c

| Artifact | Số dòng / phần tử | Vai trò cải thiện |
|---|---:|---|
| dnan_cluster_function_20260509.csv | 3,201 dòng; 3,160 body ID unique | Phân nhóm descending/ascending neuron theo function. |
| sensory_network_traversal_model_layers.feather | 166,335 node | Layer graph traversal từ sensory input. |
| mcns_fw_edge_comp.feather | 3,761,792 edge | Edge weight nam-nữ và verdict dimorphism. |
| mcns_fw_edge_comp_mappings.json | 281,656 ID; 8,586 label | Mapping body ID MaleCNS/FlyWire sang cross-match group. |
| mcns_lvl_6_hsbm_communities.feather | 311 community | Hierarchical SBM communities. |
| optic-column-type-assignments-v1.0.xlsx | 892 optic columns | Mapping L1/R7/R8 và loại optic column. |
| t-bar precision/recall | 81 ROI | QC theo neuropil ROI. |
| connection precision/recall | 81 ROI | QC edge detection theo ROI. |
| traced synapse capture | 108 ROI/compartment | Độ phủ proofread pre/post/connection. |

QC tóm tắt:

- connection precision/recall theo ROI: median lần lượt 0.917 và 0.950;
- t-bar precision/recall theo ROI: median 0.814 và 0.864;
- cross-edge verdict tổng thể: 679,283 isomorphic, 47,529 dimorphic,
  3,034,980 noise;
- cross-edge weight sum nam 51,859,473 và nữ 38,040,196.

Điểm cần sửa trong manifest tương lai: README repo vẫn dẫn archive
20250911, trong khi checkout hiện tại chứa archive 20260509:

- maxflow_sensorimotor_edges.20260509T1103.parquet.tar.gz;
- maxflow_sensorimotor_ad_expand_edges.20260508T1512.parquet.tar.gz.

Không được dùng tên file trong tài liệu cũ làm locator tự động; phải lấy tên
file từ commit đã pin và ghi checksum.

Checksum các file đã dùng:

- dnan_cluster_function_20260509.csv:
  d0d3db8f9d02af61296f9e6f28dc983c364b1937196b94645d8cecf16f5862df
- sensory_network_traversal_model_layers.feather:
  a6d0f1ad66bcd7ce576f852f4245c4d7f3e86cdb7ab9da6b5309e6183d22cf35
- mcns_fw_edge_comp.feather:
  1cac309c7760d16f5f041a7b924efbf5cdfa3a46570090fb234c2323ed9e313c
- mcns_fw_edge_comp_mappings.json:
  94aaadbefedcc314c69fb8ad62a07361c1f78ee39424bad38ac1a6d7ca4d0a12
- mcns_lvl_6_hsbm_communities.feather:
  eb583a8520bfb1f4b4fb30e3a8590cdb7e72caa599b888adce583d6de24d04a1
- optic-column-type-assignments-v1.0.xlsx:
  d4af1cacb751036f7e84bfecc9bec79ca010066ac0665599c29b566003ec080d3

Repo không có file license ở root. License của primary MaleCNS phải đối chiếu
từ nguồn chính thức; không tự suy ra toàn bộ derived repository có cùng quyền
phân phối.

### 4.2 flyconnectome/flywire_annotations tag v3.1.0

Commit đã pin:

8587524c1748ce5ef2080822a2fc890fc03bf597

Repo xác nhận annotation cho FlyWire female FAFB public release 783. File
neuron annotation có:

- 139,248 dòng, 139,248 root ID unique;
- 31 cột;
- flow intrinsic 118,497, afferent 19,262, efferent 1,489;
- dopamine 5,909 dòng;
- các cột hữu ích: supertype, top_nt, known_nt, dimorphism,
  matching_notes, fru_dsx, synonyms, fbbt_id, vfb_id.

Đối chiếu với annotation hiện tại:

- 360/360 current root ID tồn tại trong file v3.1.0;
- 360/360 cell type khớp exact;
- 360/360 neurotransmitter khớp exact;
- 39/39 current cell type có cross-match label trong mapping MaleCNS-FlyWire;
- subset edge chạm 39 current label có 54,894 edge:
  10,247 isomorphic, 398 dimorphic, 44,249 noise.

Đây là cải thiện provenance/mapping rất mạnh, nhưng file vẫn là annotation
FlyWire female. Không được gán thẳng nó làm annotation MaleCNS nếu chưa ghi
mapping và source dataset trên từng record.

Checksum:

- Supplemental_file1_neuron_annotations.tsv:
  c4bfe2722f45df80747105bea2fb4374f75cd922794dc73aef2364e5467bd34d
- Supplemental_file3_summary_with_ngl_links.csv:
  f0e740602f519d5b0b833471438d70d9ca1e074f5e7007dd42d552e4c886b313
- Supplemental_file4_hemilineages_clustering.csv:
  daa1ebbede4ff3299d36d3224c3463f4b5a36116c057261d4f6e9a55ac4cbdc2

Tên file thực tế hiện tại là file 3 = summary và file 4 = hemilineage;
điều này ngược với thứ tự trong bản đề xuất ban đầu. Repo cũng không có file
license ở root; cần xác nhận quyền sử dụng trước khi phân phối bản sao.

### 4.3 So sánh trực tiếp với trạng thái hiện tại

| Năng lực | Hiện tại | Sau vòng đánh giá | Mức cải thiện |
|---|---|---|---|
| Annotation neuron | 360 record, 39 type | 139,248 FlyWire record, 31 trường | Tăng độ sâu/quy mô; 360/360 record đã đối chiếu. |
| Edge connectivity | Chưa có edge-list MaleCNS | 3,761,792 male-female comparison edge | Có thể audit edge/weight/dimorphism; chưa chạy runtime. |
| Mapping ID | Root ID FlyWire trong CSV nhỏ | 281,656 ID tới 8,586 cross-match label | Có lớp chuyển đổi male/female rõ hơn. |
| Morphology | Chưa có skeleton/mesh target local | navis và fafbseg sẵn sàng đọc/query | Có khả năng audit hình thái; chưa tải skeleton target. |
| Query connectome | Static source catalog | neuPrint client cài được, dataset v1.0 định danh | Cần token để query. |
| Sensorimotor flow | Chưa có artifact flow local | Có maxflow archive và traversal layer | Có thể chọn target theo pathway. |
| Visual pathway | Chưa có | 892 optic-column assignments và visualpathways artifact | Mở rộng sensory/visual audit; chưa runtime. |
| Provenance | Policy/checksum có nhưng external data thiếu | Commit + checksum + schema + source-dataset audit | Reproducibility tốt hơn. |
| FlyGym rollout | Action-level proxy hiện có | Contract giữ nguyên; runtime smoke thật đạt | Không có bằng chứng connectome làm rollout sinh học hơn. |

Tỷ lệ 139,248 / 360 chỉ là chênh lệch số record annotation, không phải
tuyên bố coverage sinh học trực tiếp vì scope hai bảng khác nhau.

## 5. Đánh giá từng repo

### connectome-neuprint/neuprint-python — P0

- Clone commit: d89e624b445340f3deb0ace7998b219af57a75ad.
- Package cài thành công: 0.6.3.
- Source smoke cùng commit: import 0.6.3 và token gate đạt.
- Live query MaleCNS chưa chạy vì NEUPRINT_APPLICATION_CREDENTIALS chưa có.

Cải thiện: truy vấn neuron, cell type, upstream/downstream và adjacency bằng
API chính thức. Không tự tạo edge checkpoint hoặc rollout.

### navis-org/navis — P1

- Clone HEAD: cb9a5915b6b3587cb81154f4f77ffc62fe12b03a.
- Source HEAD khai báo 2.0.0-rc.1, cần sparse-cubes và navis-fastcore; import
  và skeleton smoke đạt sau khi bổ sung dependency.
- Test chọn lọc source HEAD: 105 passed, 4 failed, 3 skipped.
- Bốn failure cùng nhóm precomputed skeleton/mesh writer trên Windows, lỗi
  tạo đường dẫn info/info.
- Bản PyPI 1.12.0 import và skeleton smoke đạt.

Khuyến nghị: dùng navis 1.12.0 cho audit đầu tiên; chỉ chuyển sang HEAD
2.0.0-rc.1 sau khi có workaround/test fix cho Windows precomputed writer.
Không đưa navis vào FlyGym runtime.

### navis-org/fafbseg-py — P1 nếu cần FlyWire/FAFB sâu

- Clone commit: d0da95123ee606e204ae2c702e7bc78538646fbd.
- Cài thành công fafbseg 3.2.2 trên Windows/Python 3.12.
- Import FlyWire module, NeuronCriteria và helper discovery đạt offline.
- Live CAVE/FlyWire query chưa chạy do thiếu credential/service session.

Cải thiện: có đường lấy annotation, mesh, skeleton và connectivity FlyWire.
Chi phí: cloud-volume/CAVE dependency lớn và access/auth phức tạp; để ngoài
runtime.

### reiserlab/visualpathways — P2

- Clone commit: 23f6ac131529b5f56894c6eeb9b88b17894fc00d.
- Checkout khoảng 1.9 GB, chủ yếu gồm kết quả/HTML figure.
- Python source compile đạt.
- Không cài full dependency và không chạy pipeline figure vì có nhiều
  dependency nặng, git dependency/fork và dữ liệu external.

Cải thiện: tham khảo visual pathway, VCBN/VPN, visual input contribution và
optic pathway. Không phải package runtime.

### natverse/malecns — P1 cho nhóm dùng R

- Clone commit: daf8e2a9849cc77695b14bb6b9d4c02456cd3b3c.
- Metadata 0.4.2.9000, GPL-3; mặc định đọc snapshot male-cns:v1.0.
- Không cài/chạy vì máy không có Rscript.
- README yêu cầu NeuPrint token và, cho thao tác Clio, credential khác.

Cải thiện: access MaleCNS bằng natverse, metadata, mesh và transform. Cần R
environment riêng.

### natverse/coconatfly — P1/P2

- Clone commit: c33ae3d7c2f1a9b253384ddd11cf76beb02a81e7.
- Metadata 0.2.4.9000, GPL >=3, lifecycle experimental.
- Không cài/chạy do thiếu R và natverse dependency chain.

Cải thiện: comparative analysis giữa hemibrain, FlyWire, MANC, MaleCNS, FANC
và dataset khác. Không coi là dependency bắt buộc.

### funkelab/synister_malecns — P2

- Clone commit: 538150285128687ea454827dbdc6666d592fdb2e.
- Python scripts compile đạt.
- Không chạy inference: repo khai báo Linux-64/pixi, máy không có pixi,
  WSL chỉ có docker-desktop đang stopped, không có ground-truth, checkpoint
  hoặc volume path /groups và /nrs.

Cải thiện tiềm năng: neurotransmitter prediction từ EM volume. Không giải
quyết mapping edge-to-action.

### alextitonis/fly.ai — P2 sandbox

- Clone commit: 0aa078055f7a975075ba5baf1156430f9e606356.
- Editable install flybrain 0.1.0 đạt trong sandbox.
- flybrain --version và flybrain info đạt.
- Brain weights không có local; chưa chạy whole-brain LIF.

Cải thiện tiềm năng: LIF/reservoir trên MaleCNS, visual encoder và readout.
Hạn chế: repo cộng đồng, không tích hợp FlyGym/MuJoCo action contract, không
dùng để thay thế nguồn MaleCNS hoặc validation sinh học.

## 6. Đã hoàn thiện và chưa hoàn thiện

### Đã hoàn thiện

1. Cài đặt Python analysis stack tách biệt, không làm bẩn runtime core.
2. Có commit thực tế của từng repo.
3. Có data schema, row count, duplicate và checksum audit cho hai nguồn chính.
4. Current annotation 360 neuron đã join được vào FlyWire v3.1.0 và mapping
   2025malecns.
5. Action-level proxy đã chạy qua public contract sau khi cài đúng runtime.
6. Các failure do Windows, runtime và toolchain đã được ghi rõ.

### Chưa hoàn thiện

1. Chưa tải primary MaleCNS body annotation, full connectivity, synapse
   partners, skeleton hoặc mesh từ release v1.0.
2. Chưa có schema normalize chính thức giữa root_id FlyWire và bodyId MaleCNS.
3. Chưa đưa 3,761,792 cross edges vào prepare_neural_checkpoint.py.
4. Chưa có neural runner trong platform tiêu thụ checkpoint edge.
5. Chưa query được NeuPrint/CAVE vì thiếu token.
6. Chưa chạy R/natverse hoặc pixi/GPU inference.
7. navis HEAD còn lỗi Windows precomputed writer; dùng PyPI 1.12.0 tạm thời.
8. Hai repo data annotation không có license file ở root; cần review pháp lý.
9. Full platform có hai failure turning metric ở duration ngắn.

## 7. Kiến trúc và kế hoạch tích hợp

external/2025malecns và external/flywire_annotations_3.1.0
  -> connectome_intake / mapping_audit
  -> root_id, bodyId, source_dataset, map_method, checksum
  -> neural checkpoint preparation, nếu đủ gate
  -> drosophila-pd-flygym Perturbation action hook
  -> rollout và locomotion metric, chỉ khi có neural consumer thật

### P0

- Giữ commit/checksum trong manifest machine-readable.
- Viết schema adapter cho root_id, bodyId, source_dataset, mapping_status,
  cell_type, supertype, neurotransmitter và side.
- Tạo connectivity_audit cho 39 current label; xuất edge counts, verdict và
  provenance, không gọi là rollout.
- Khi có NeuPrint token, chạy query read-only cho danh sách target nhỏ và lưu
  response checksum.

### P1

- Tải tối thiểu body annotation và vài skeleton target từ MaleCNS v1.0; không
  tải partner table 6.8 GB khi chưa có storage plan.
- Dùng navis 1.12.0 để visualize/audit skeleton.
- Tạo Linux/WSL environment riêng nếu cần natverse hoặc FAFB sâu.

### P2

- Chỉ mở visualpathways khi visual input là hypothesis chính.
- Chỉ mở synister_malecns khi có EM volume, ground truth và GPU.
- Chỉ dùng fly.ai trong sandbox để so sánh LIF, không nhập kết quả vào claim.

## 8. Tiêu chí nghiệm thu vòng kế tiếp

Artifact connectome chỉ được promote vào checkpoint khi có đủ:

- dataset/release rõ: male-cns:v1.0 hoặc FlyWire 783;
- source repo commit và file checksum;
- schema có source/target dataset và ID namespace;
- mapping male/female trên từng record;
- target neuron/edge có annotation và provenance;
- duplicate ID được kiểm soát;
- test pass cho import/transform/query offline;
- runtime có consumer thực sự nếu muốn gọi là rollout;
- claim lock giữ nguyên: computational proxy không đồng nghĩa biological
  Parkinson validation.

## 9. Nguồn chính thức

- https://male-cns.janelia.org/
- https://male-cns.janelia.org/download/
- https://pypi.org/project/neuprint-python/
- https://navis-org.github.io/navis/installation/
- https://fafbseg-py.readthedocs.io/en/latest/source/install.html
- https://github.com/flyconnectome/flywire_annotations/releases/tag/v3.1.0
