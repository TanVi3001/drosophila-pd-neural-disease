# Disease mapping và target neuron

Thư mục này ghi lại mapping có provenance để chạy thử một condition neural-level. Đây
không phải database kết luận sinh học và không tự suy ra neuron từ tên gene.

## Mapping hiện có

Condition dopamine_deficiency.exploratory.yaml dùng 342 root ID trong FlyWire v783.
Các ID được chọn từ bảng annotation có cell_type bắt đầu bằng PAM, PPL hoặc PPM và
top_nt=dopamine; sau đó đã kiểm tra tất cả đều có trong
2025_Completeness_783.csv của connectome đang chạy.

Paper Riemensperger et al. (2011) cung cấp bằng chứng về mô hình thiếu dopamine và
phenotype locomotion, nhưng không cung cấp các FlyWire root ID này. Vì vậy mapping
giữa paper và ID là mapping computational có hai nguồn, không phải phát hiện
cell-specific của paper.

## Trạng thái theo gene

| Condition | Trạng thái | Lý do |
| --- | --- | --- |
| dopamine deficiency | MAPPED_EXPLORATORY | Có paper locomotion và tập ID dopamine từ FlyWire; chưa calibration |
| PINK1 | WAITING_NEURON_EVIDENCE | Chưa có mapping neuron-ID được review trong repo |
| Parkin | WAITING_NEURON_EVIDENCE | Chưa có mapping neuron-ID được review trong repo |
| DJ-1 | WAITING_NEURON_EVIDENCE | Chưa có mapping neuron-ID được review trong repo |
| LRRK2 | WAITING_NEURON_EVIDENCE | Chưa có mapping neuron-ID được review trong repo |
| alpha-synuclein | WAITING_NEURON_EVIDENCE | Driver pan-neuronal không đủ để chọn một tập ID cụ thể |

## Cách đọc kết quả

Condition exploratory chỉ cho phép kiểm tra pipeline và độ nhạy locomotion của
perturbation trên connectome thật. Không gọi kết quả là validation Parkinson, không
đồng nhất presynaptic gain với nồng độ dopamine và không dùng làm bằng chứng đáp ứng
thuốc.

Nguồn local của annotation có license CC BY-NC 4.0 theo
external/fly-brain-audit/source_manifest.json; code nguồn audit có license MIT.
Không chép toàn bộ connectome vào repository.

## Nguồn paper dùng cho mapping lớp tế bào

- Riemensperger et al. 2011: https://pmc.ncbi.nlm.nih.gov/articles/PMC3021077/
- Clark et al. 2006, PINK1: https://pubmed.ncbi.nlm.nih.gov/16672981/
- Sang et al. 2007, Parkin: https://pmc.ncbi.nlm.nih.gov/articles/PMC6673194/
- Tanti et al. 2005, DJ-1: https://doi.org/10.1016/j.gene.2005.06.040
- Imai et al. 2008, LRRK2: https://pmc.ncbi.nlm.nih.gov/articles/PMC2268198/
- Riemensperger et al. 2013, alpha-synuclein: https://pubmed.ncbi.nlm.nih.gov/24239353/

Các nguồn trên chứng minh paper có nghiên cứu neuron dopaminergic hoặc phenotype
locomotion ở mức cell class/driver. Chúng không chứa bảng chuyển đổi trực tiếp
từ paper sang 342 FlyWire root ID; phần này phải được xem là một giả định
computational có thể kiểm tra, không phải ground truth sinh học.
