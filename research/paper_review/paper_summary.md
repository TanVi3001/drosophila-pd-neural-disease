# Tóm tắt và phân tích 6 paper về phenotype vận động ở Drosophila

Ngày audit nguồn: 2026-08-28
Người thực hiện: `AUTOMATED_SOURCE_AUDIT`
Trạng thái: `CANDIDATE_REVIEW_REQUIRED`

## Phạm vi và nguyên tắc

Tài liệu này là bản đọc và đối chiếu tự động từ các nguồn công khai đã đăng ký trong `datasets/literature_phenotypes/paper_registry.csv`. Mỗi dòng trong [paper_analysis_vi.csv](paper_analysis_vi.csv) tương ứng với một record trong `phenotype_records.csv`.

Các giá trị được giữ đúng statistic và assay mà paper báo cáo. Không đổi median thành mean, không đổi SE/SEM/IQR thành SD, không đọc số từ chiều cao cột, và không đổi DAM count hoặc climbing score thành walking speed. Những phần chỉ có trên figure hoặc còn thiếu provenance được giữ ở trạng thái chờ reviewer con người.

**Ranh giới khoa học:** các paper dưới đây là bằng chứng phenotype trên ruồi thật. Việc chúng được đưa vào workspace không xác nhận mô hình computational của repository, không phải biological Parkinson validation, không phải chẩn đoán, dự đoán lâm sàng hay đánh giá thuốc.

## 1. Riemensperger et al. (2011)

- **Tiêu đề:** *Behavioral consequences of dopamine deficiency in the Drosophila central nervous system*.
- **Nguồn:** PNAS; DOI `10.1073/pnas.1010930108`; PMID `21187381`; [PubMed](https://pubmed.ncbi.nlm.nih.gov/21187381/); [PMC](https://europepmc.org/articles/PMC3021077).
- **Mô hình:** `DTHgFS±; ple`, tạo thiếu dopamine trong hệ thần kinh nhưng vẫn cứu phát triển ngoại biên; các nhóm rescue và WT được dùng làm đối chứng.
- **Tuổi, giới và assay:** ruồi trưởng thành 2-5 ngày trong phần phương pháp; Figure 2A mô tả ruồi 5 ngày. Record hiện hành ghi nhóm nữ và 13 flies, nhưng thông tin giới cần được reviewer xác nhận lại từ protocol gốc.
- **Đo lường:** ruồi bị bất hoạt cánh đi tự do trong arena mở 15 phút; paper báo walking speed và covered distance. Kết quả mục tiêu là median walking speed `7.8 mm/s`; nhóm rescue `10.8 mm/s`, WT `15 mm/s`. Covered distance được báo theo median nhưng không phải record mục tiêu hiện tại.
- **Độ phân tán:** Figure 2A có median, mean, quartiles, quantiles và extreme values. Không có một uncertainty số học riêng cho median 7.8 trong record hiện tại.
- **Supplementary:** chưa có supplementary hợp lệ được giữ trong intake hiện tại; manifest ghi `NOT_IDENTIFIED_IN_INTAKE`.
- **Đánh giá:** `★★★★☆` cho việc mô tả giảm vận động có định lượng; `★★☆☆☆` cho chuyển đổi trực tiếp sang FlyGym vì statistic là median và protocol 15 phút khác endpoint hiện tại.
- **Sử dụng đề xuất:** validation candidate hoặc calibration candidate có điều kiện, chỉ sau khi xác nhận statistic, giới tính, sample size và quy tắc chuyển assay. Không dùng như mean target ngay lập tức.

## 2. Pokrzywa et al. (2017)

- **Tiêu đề:** *Effects of small-molecule amyloid modulators on a Drosophila model of Parkinson's disease*.
- **Nguồn:** PLOS ONE; DOI `10.1371/journal.pone.0184117`; PMID `28863169`; [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5581160/).
- **Mô hình:** ruồi cái mới nở biểu hiện human alpha-synuclein bằng `w; +; UAS-Hsap/nSyb-Gal4`; control là `w; +; UAS-Hsap/+`.
- **Tuổi, giới và assay:** đo theo các mốc 1, 7, 16, 21, 30 và 42 ngày; 10 ruồi/vial, 3-10 vial độc lập, hai chuỗi ghi hình/vial được lấy trung bình. FlyTracker ghi hình 30 fps trong 10 giây và tính nhiều chỉ số vận động.
- **Đo lường:** mean velocity, maximum velocity, total walking duration, total walking distance, trajectory length và phần trăm thời gian chuyển động. Record hiện tại giữ mean velocity `5.6 mm/s` ở ngày 1 và `2.5 mm/s` ở ngày 21 cho alpha-synuclein; control lần lượt `6.0` và `5.0 mm/s`.
- **Độ phân tán:** chú thích Figure 2 ghi error bars `± SE`, nhưng SE số học của bốn record chưa xuất hiện trong phần text hoặc S1 Table đã kiểm tra. Không tự đo từ cột.
- **Supplementary:** có supplementary package và S1 Table được giữ; S1 Table chủ yếu là kiểm định, không cung cấp đầy đủ SE số học cho các record này.
- **Đánh giá:** `★★★★★` cho khả năng tương thích khái niệm với locomotion metrics; `★★★☆☆` cho calibration trực tiếp vì còn khác biệt giữa vial/2D FlyTracker và FlyGym.
- **Sử dụng đề xuất:** ứng viên tốt nhất trong sáu paper cho validation/candidate calibration của velocity theo tuổi, nhưng phải phê duyệt assay transfer và uncertainty trước.

## 3. Dumitrescu et al. (2023)

- **Tiêu đề:** *Parkin Knockdown Modulates Dopamine Release in the Central Complex but Not the Mushroom Body Heel, of Aging Drosophila*.
- **Nguồn:** ACS Chemical Neuroscience; DOI `10.1021/acschemneuro.2c00277`; PMID `36576890`; [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9897283/).
- **Mô hình:** `UAS-mCD8-GFP; TH-GAL4/UAS-parkin-RNAi`, knockdown trong nhóm neuron TH/dopaminergic; đối chứng là dòng TH-GAL4 phù hợp.
- **Tuổi, giới và assay:** nam ruồi; nhóm 1 dpe và 45 dpe, với tuổi trung bình lúc bắt đầu theo dõi 7 ngày cũng được nêu trong chú thích. DAM theo dõi 7 ngày theo chu kỳ sáng/tối 12:12.
- **Đo lường:** số lần ruồi cắt tia hồng ngoại trong ống, được báo là average daily counts per fly. Hoạt động tương đối giảm khoảng `30%` ở nhóm parkin-RNAi 1 dpe và `85%` ở nhóm 45 dpe; sample size tương ứng `n=29` và `n=52`.
- **Độ phân tán:** Figure 1 ghi error bars là SEM cho activity levels, nhưng record hiện tại chỉ lưu chênh lệch tương đối nên không có uncertainty số học tương ứng.
- **Supplementary:** paper có Supporting Information gồm phương pháp bổ sung, 10 supplementary figures và 1 supplementary table; bản PDF gốc chưa được giữ do máy chủ PMC yêu cầu challenge tải xuống, còn bản toàn văn BioC được lưu làm fallback.
- **Đánh giá:** `★★★☆☆` cho bằng chứng age-dependent activity; `★☆☆☆☆` cho chuyển thành FlyGym walking speed.
- **Sử dụng đề xuất:** validation-only cho activity/age trend. Không chuyển DAM beam-break count thành `mm/s`, không đưa vào calibration velocity.

## 4. Pozo et al. (2022)

- **Tiêu đề:** *An Early Disturbance in Serotonergic Neurotransmission Contributes to the Onset of Parkinsonian Phenotypes in Drosophila melanogaster*.
- **Nguồn:** Cells; DOI `10.3390/cells11091544`; PMID `35563850`; [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9105628/).
- **Mô hình:** `Pink1B9` so với `w1118` control.
- **Tuổi, giới và assay:** ruồi 28 ngày tuổi; phần record trích xuất hiện chưa xác nhận giới. Ruồi đơn được ghi hình trong arena tròn đường kính 39 mm, cao 2 mm, trong 3 phút ở nhiệt độ phòng; phân tích bằng CeTrAn.
- **Đo lường:** distance traveled và activity time. Không điều trị, `Pink1B9` có distance `62.091 mm` so với control `323.326 mm`; activity time `11.865 s` so với `51.894 s`. Sample size là 21 và 20 cho distance/activity theo nhóm tương ứng.
- **Độ phân tán:** phần văn bản dùng ký hiệu `±`, trong khi chú thích Figure 3 nói dữ liệu được trình bày bằng interquartile range với maximum/minimum ranges. Vì vậy các số `61.288`, `236.209`, `12.914`, `32.409` được giữ nguyên nhưng không gán là SD hay SE.
- **Supplementary:** supplementary package đã được giữ và được ghi trong manifest.
- **Đánh giá:** `★★★★☆` cho distance cùng thời lượng đo rõ; `★★☆☆☆` cho chuyển trực tiếp sang FlyGym vì khác arena, thời lượng và statistic spread.
- **Sử dụng đề xuất:** validation candidate cho distance/activity sau khi xác nhận sex, statistic label, thời lượng và quy tắc chuẩn hóa. Activity time không phải walking speed.

## 5. Hwang et al. (2013)

- **Tiêu đề:** *Drosophila DJ-1 Decreases Neural Sensitivity to Stress by Negatively Regulating Daxx-Like Protein through dFOXO*.
- **Nguồn:** PLOS Genetics; DOI `10.1371/journal.pgen.1003412`; PMID `23593018`; [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3616925/).
- **Mô hình:** `DJ-1betaex54` so với WT, cùng các nhóm DLP mutant/double mutant trong Figure 5E.
- **Tuổi, giới và assay:** Figure 5E dùng ruồi 5 ngày tuổi. Protocol climbing chuyển 10 ruồi đực vào lọ, thích nghi 1 giờ, gõ xuống đáy và đếm số ruồi lên đỉnh trong 4 giây; thực hiện 10 trial và lặp với các dòng độc lập.
- **Đo lường:** climbing score là tỷ lệ ruồi lên đỉnh trên tổng số ruồi, biểu diễn phần trăm. Chú thích Figure 5E ghi mean ± s.e., `n >= 12`, và khác biệt thống kê; tâm số của nhóm DJ-1betaex54 không được nêu trong text extraction.
- **Độ phân tán:** convention là SE nhưng giá trị SE số học chưa có. Không lấy chiều cao cột để điền số.
- **Supplementary:** supplementary package đã được giữ.
- **Đánh giá:** `★★★☆☆` cho validation của climbing phenotype; `★☆☆☆☆` cho calibration speed vì endpoint là tỷ lệ leo trong 4 giây.
- **Sử dụng đề xuất:** validation-only hoặc disease signature qualitative/ordinal. Chỉ chuyển sang metric khác sau khi nhóm nghiên cứu định nghĩa assay bridge hợp lệ.

## 6. Godena et al. (2014)

- **Tiêu đề:** *Increasing microtubule acetylation rescues axonal transport and locomotor deficits caused by LRRK2 Roc-COR domain mutations*.
- **Nguồn:** Nature Communications; DOI `10.1038/ncomms6245`; PMID `25316291`; [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4208097/).
- **Mô hình:** human LRRK2 `R1441C` và `Y1699C` biểu hiện trong motor neuron bằng `D42-GAL4`; các nhóm WT/G2019S/control và rescue được dùng trong paper.
- **Tuổi, giới và assay:** climbing được thực hiện sau 5 ngày, tức động vật khoảng 6-7 ngày tuổi; giới không được xác nhận trong record hiện tại. Paper đồng thời đo flight và axonal transport.
- **Đo lường:** climbing index và flight index; R1441C/Y1699C gây giảm locomotion, còn tăng acetyl hóa vi ống hoặc can thiệp liên quan có thể rescue. Record hiện tại tập trung Figure 6C và Supplementary Figure 3C, với nhóm untreated `n=43` cho R1441C và `n=59` cho Y1699C.
- **Độ phân tán:** figure legend dùng mean ± s.e.m./SEM theo chart, nhưng tâm số untreated và SEM số học chưa có dạng text. Không tự trích số từ cột.
- **Supplementary:** supplementary package đã được giữ; Supplementary Figure 3C được ghi nhận trong record.
- **Đánh giá:** `★★★☆☆` cho validation locomotor có liên quan motor neuron; `★☆☆☆☆` cho chuyển sang current FlyGym brain-only mapping.
- **Sử dụng đề xuất:** validation-only ở mức phenotype direction. Cần review phạm vi motor neuron/VNC và mapping có provenance trước mọi diễn giải gene-specific.

## Thuật ngữ dễ hiểu

- **Locomotion:** khả năng di chuyển, gồm đi bộ, leo hoặc chạy.
- **Phenotype:** đặc điểm quan sát được, ví dụ vận tốc thấp hơn hoặc ít leo hơn.
- **Negative geotaxis:** gõ ruồi xuống đáy rồi đo khả năng leo lên.
- **FlyTracker/CeTrAn:** hệ thống ghi hình và phần mềm theo dõi đường đi của ruồi.
- **DAM beam-break:** số lần ruồi cắt tia hồng ngoại; là chỉ số hoạt động trong thiết bị DAM, không tự động là vận tốc.
- **Median:** giá trị giữa của phân bố; không đồng nghĩa với mean.
- **SE/SEM:** sai số chuẩn được paper dùng cho trung bình; không được đổi thành SD.
- **IQR:** khoảng tứ phân vị; mô tả độ rộng ở giữa phân bố và không được đổi thành SD.

## Kết luận audit

Có 6 paper thật, 14 candidate phenotype và 5 PDF gốc đã tải thành công. Toàn bộ candidate vẫn ở `PENDING_HUMAN_SIGNOFF`; `reviewer_2` vẫn là `NOT_ASSIGNED`. Chưa có target nào được phê duyệt cho calibration hoặc holdout.

Tài liệu này đủ để nhóm nghiên cứu bắt đầu review có cấu trúc. Nó chưa đủ để chuyển candidate thành target calibration vì vẫn còn các blocker: reviewer thứ hai, uncertainty số học hoặc statistic label, assay transfer, và mapping gene-specific có provenance. Xem [paper_pdf_manifest.csv](paper_pdf_manifest.csv) để biết hash và trạng thái từng PDF.
