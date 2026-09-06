# Sàng lọc nguồn paper

## Mục đích

Danh sách này phân biệt nguồn được giữ cho dự án với nguồn chỉ có trong thư mục tham khảo của nhóm. Đây là sàng lọc nguồn, không phải kết quả trích xuất phenotype và không phải phê duyệt calibration target.

## Corpus được chọn

Các nguồn canonical nằm trong `temporary/paper_pdf/curated_sources/` và được ghi hash trong `selected_sources.csv`. Nhóm disease/locomotion chính gồm Riemensperger 2011, Riemensperger 2013, Pokrzywa 2017, Pozo 2022, Hwang 2013, Godena 2014, Cha 2005, Haywood 2004, Liu 2008, Aggarwal 2019 và Poddighe 2014.

Ba nguồn được giữ với giới hạn rõ ràng:

- Dumitrescu 2023: chỉ có supporting information trong thư mục hiện tại; DAM activity không được đổi thành walking speed.
- Pugliese 2025: preprint về CPG/connectome, dùng cho phương pháp và bối cảnh neural control, không phải disease evidence.
- Liessem 2026: nghiên cứu walking direction/dopaminergic control, dùng để định nghĩa turning/direction, không tự tạo disease target.
- NeuroMechFly v2 2024: paper nền tảng FlyGym, dùng để trích dẫn runtime/model provenance, không phải phenotype Parkinson.

Poddighe 2014 được đánh dấu `SELECTED_WITH_RESTRICTION` vì cần người phụ trách kiểm tra Expression of Concern trước khi dùng trong lập luận khoa học. Không dùng paper này làm target calibration khi chưa có quyết định bằng văn bản.

## Nguồn loại khỏi corpus disease

| File | Quyết định | Lý do |
|---|---|---|
| `cshperspectmed-PKD-a009399.pdf` | Loại khỏi evidence | Review tổng quan, không phải primary data cho target hiện tại. |
| `Quantitative_Gait_Evaluation_in_the_Clinic.pdf` | Loại khỏi calibration | Gait người/clinical context; không phải dữ liệu Drosophila và không quy đổi tự động sang FlyGym. |
| `SharedmushroombodycircuitsunderlievisualandolfactorymemoriesinDrosophila.pdf` | Loại | Không liên quan trực tiếp đến Parkinson locomotion. |
| `Deep_Reinforcement_Learning-Based_Joint_Resource_Allocation_and_Trajectory_Design_for_UAV-Assisted_Multi-Cell_ISAC_Systems.pdf` | Loại | Bài IEEE về UAV/viễn thông, không thuộc khoa học ruồi giấm hay Disease Layer. |
| `E-OptEEG_A_Hybrid_Ensemble_Metaheuristic_Feature_Optimization_for_EEG-Based_Sentiment_Analysis_on_Resource-Constrained_Edge_Devices.pdf` | Loại | EEG sentiment analysis, không liên quan. |
| `FireFly_v2_Advancing_Hardware_Support_for_High-Performance_Spiking_Neural_Network_With_a_Spatiotemporal_FPGA_Accelerator.pdf` | Không đưa vào disease corpus | Có thể tham khảo về phần cứng SNN, nhưng không hỗ trợ phenotype hay calibration của mô hình này. |
| `MoMo_-_Combining_Neuron_Morphology_and_Connectivity_for_Interactive_Motif_Analysis_in_Connectomes.pdf` | Không đưa vào disease corpus | Công cụ phân tích connectome; chỉ dùng nếu viết phần phương pháp trực quan hóa. |
| `ViMO_-_Visual_Analysis_of_Neuronal_Connectivity_Motifs.pdf` | Không đưa vào disease corpus | Công cụ trực quan hóa motif; không phải evidence locomotion/disease. |

Các bản trùng ở `Nhóm PP Tầng A` và `Nhóm PP tầng B` không bị xóa để bảo toàn thư mục gốc; chỉ một bản canonical được tham chiếu trong registry.

## Quy tắc license và phát hành

PDF trong `temporary/` bị loại khỏi Git bởi `.gitignore`, do đó không tự động được đẩy lên GitHub. Khi public paper, chỉ đưa metadata, DOI/PMID, URL chính thức, hash và giấy phép hợp lệ; chỉ phân phối PDF nếu license cho phép hoặc nhóm có quyền phân phối. `LICENSE_REVIEW_REQUIRED` không có nghĩa là paper không hợp lệ về khoa học; đó là cờ kiểm tra quyền sử dụng file.
