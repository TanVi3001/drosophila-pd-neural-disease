# Candidate phenotype dataset

Đây là bộ trích xuất có provenance để chuẩn bị review thủ công. Mỗi record liên
kết tới một paper trong `paper_registry.csv` và giữ nguyên loại assay của paper.

## Quy tắc

1. Không quy đổi DAM counts, climbing score hoặc activity percentage thành
   `mm/s` nếu chưa có chính sách transfer assay được phê duyệt.
2. Không điền uncertainty từ độ cao cột hoặc error bar nếu chưa có hai reviewer.
3. `pending_second_reviewer` không được dùng cho calibration hoặc holdout.
4. `qualitative_only` chỉ hỗ trợ disease mapping, không phải numeric target.
5. Neuron root ID phải có provenance độc lập; gene name không tự động ánh xạ
   thành một tập neuron FlyWire.

## Nguồn định lượng hiện có

- Riemensperger et al. 2011: spontaneous walking trong open arena.
- Pokrzywa et al. 2017: FlyTracker velocity theo tuổi.
- Dumitrescu et al. 2023: DAM activity theo tuổi ở Parkin-RNAi.
- Pozo et al. 2022: distance và activity time ở Pink1-B9 tại 28 ngày.
- Hwang et al. 2013: DJ-1beta climbing, đang chờ đọc giá trị từ Figure 5E.
- Godena et al. 2014: LRRK2 variant climbing, đang chờ đọc Figure 6C.

Các giá trị này chưa được tự động đưa vào `calibration_targets/targets.csv`.
