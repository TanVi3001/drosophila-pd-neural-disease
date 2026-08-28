# Rà soát target literature

File `targets.csv` hiện chứa hai target ứng viên được chuyển từ hồ sơ nghiên
cứu trước của project. Các giá trị có nguồn công khai và được giữ nguyên đơn
vị, nhưng chưa được nhóm nghiên cứu phê duyệt để hiệu chuẩn.

## Nguồn

- Riemensperger et al. (2011), PNAS, DOI `10.1073/pnas.1010930108`, PMID `21187381`, [toàn văn PMC3021077](https://pmc.ncbi.nlm.nih.gov/articles/PMC3021077/). Bài báo nêu median walking speed `7.8 mm/s` ở ruồi trưởng thành 5 ngày tuổi bị thiếu dopamine thần kinh; vị trí nguồn là Figure 2A và phần Results.
- Pokrzywa et al. (2017), PLOS ONE, DOI `10.1371/journal.pone.0184117`, [toàn văn PMC5581160](https://pmc.ncbi.nlm.nih.gov/articles/PMC5581160/). Bài báo mô tả mean velocity của nhóm biểu hiện alpha-synuclein giảm từ `5.6 mm/s` xuống `2.5 mm/s` trong ba tuần đầu; dòng target giữ mốc `2.5 mm/s` và đánh dấu cần xác nhận tuổi chính xác.

## Trạng thái

Hai dòng đang có `review_status=pending`. Script so sánh chỉ sử dụng dòng có
`review_status=approved`, vì vậy việc thêm file này không kích hoạt calibration
và không tạo kết quả khoa học.

## Checklist phê duyệt thủ công

- [ ] Đã đọc phần Methods, Results, Figure và Supplementary của từng paper.
- [ ] Đã xác nhận genotype/model, tuổi và giới tính.
- [ ] Đã xác nhận statistic (median/mean), sample size và variance.
- [ ] Đã xác nhận assay, đơn vị và thời lượng đo.
- [ ] Đã kiểm tra endpoint có thể so sánh với `mean_planar_speed_mm_s` hay không.
- [ ] Đã quyết định dòng này thuộc calibration hay holdout, không dùng đồng thời.
- [ ] Hai reviewer đã ghi nhận quyết định và ngày review.
- [ ] Chỉ sau các bước trên mới đổi trạng thái thành `approved`.

## Ranh giới khoa học

Đây là target locomotion tính toán có điều kiện. Nó không biến dữ liệu
behavioral của ruồi thật thành bằng chứng rằng mô hình là Parkinson sinh học,
không phải chẩn đoán, dự đoán lâm sàng hay đánh giá thuốc.
