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

## Kiểm định bổ sung trước khi phê duyệt

Bảng dưới đây tách rõ thông tin đã đọc được trực tiếp từ bài báo và thông tin
vẫn còn thiếu. Không dòng nào được xem là calibration target cho đến khi người
review điền đủ phần còn thiếu và chọn mục đích sử dụng.

| Paper | Thông tin đã xác nhận | Còn thiếu | Quyết định đề nghị |
| --- | --- | --- | --- |
| `riemensperger_2011_dopamine_deficiency` | Ruồi trưởng thành 5 ngày tuổi trong Figure 2A; phần Methods/SI nêu mặc định thí nghiệm locomotion dùng ruồi cái 3-5 ngày tuổi; median walking speed 7.8 mm/s; open arena; Figure 2A/Results; DOI và PMID đã ghi trong CSV. | Sample size của endpoint, variance số học (bài hiển thị median/quartiles nhưng target chưa có giá trị số), genotype notation đầy đủ và quy tắc chuyển assay open arena sang FlyGym flat-ground. | Giữ `pending`; chỉ phê duyệt sau khi research lead xác nhận tính tương đồng assay và điền provenance review. |
| `pokrzywa_2017_alpha_syn_flytracker` | Mô hình biểu hiện human alpha-synuclein bằng `nSyb-GAL4`; FlyTracker; các mốc tuổi 1, 7, 16, 21, 30, 42 ngày; mean velocity giảm từ 5.6 xuống 2.5 mm/s trong ba tuần đầu; ruồi cái, 10 ruồi mỗi vial, 3-10 vial độc lập, hai recording mỗi vial được lấy trung bình. | Giá trị 2.5 chưa gắn với một mốc tuổi đơn lẻ; SE được báo theo hình nhưng chưa có giá trị số cho endpoint này; quy tắc chuyển FlyTracker trong vial sang FlyGym. | Không dùng làm target calibration đơn mốc; có thể xem xét làm target theo đường cong tuổi sau khi trích đầy đủ bảng/figure và được review. |

### Quy tắc phân tách calibration và holdout

- Mỗi endpoint chỉ được gán một vai trò: `calibration` hoặc `holdout`, không dùng
  đồng thời cho cả hai.
- Target khác assay, khác đơn vị, hoặc khác định nghĩa metric không được gộp
  vào một loss nếu chưa có quy tắc chuyển đổi được phê duyệt.
- Không ước lượng sample size, variance, tuổi hoặc giới tính từ biểu đồ nếu
  bài báo không ghi rõ.
- Nếu không thể quy đổi thành `mean_planar_speed_mm_s` mà không thêm giả định,
  giữ trạng thái `pending` và ghi `not_comparable` trong ghi chú review.

### Nguồn để research lead kiểm tra

- Riemensperger et al. 2011: [PMC3021077](https://pmc.ncbi.nlm.nih.gov/articles/PMC3021077/).
- Pokrzywa et al. 2017: [PMC5581160](https://pmc.ncbi.nlm.nih.gov/articles/PMC5581160/).

## Dataset candidate mở rộng

Paper registry và 14 phenotype record có provenance nằm trong
[`../datasets/literature_phenotypes/`](../datasets/literature_phenotypes/). Bộ
này bổ sung PINK1 định lượng và đăng ký hàng đợi đọc hình cho DJ-1/LRRK2. Không
record nào được coi là `approved`; việc chuyển record sang file target vẫn là
quyết định thủ công của nhóm nghiên cứu.
