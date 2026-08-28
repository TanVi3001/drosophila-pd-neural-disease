# Calibration targets

Chỉ nhập target từ paper đã được nhóm nghiên cứu duyệt. Không nhập giá trị
ước lượng từ hình nếu chưa xác nhận, không trộn assay khác nhau và không dùng
một target vừa để fit vừa để holdout.

Template đang để trống để tránh tạo dữ liệu khoa học giả.

## Quy trinh nhap va phe duyet

1. Them mot dong cho moi endpoint da doc truc tiep tu paper.
2. Dien provenance, assay, don vi, statistic, sample size va variance. Neu
   paper khong bao cao truong nao thi de trong va ghi ro trong `notes`.
3. Giu `review_status=pending` trong khi chua review.
4. Research lead kiem tra Methods, Results, figure va supplementary, sau do
   ghi quyet dinh trong `notes` theo mau:

   `reviewer=TEN;review_date=YYYY-MM-DD;allocation=calibration`

   hoac:

   `reviewer=TEN;review_date=YYYY-MM-DD;allocation=holdout`

5. Chi doi sang `review_status=approved` khi target duoc phe duyet va endpoint
   co the so sanh voi metric cua simulation. Khong dung mot target cho ca
   calibration va holdout.

## Kiem tra readiness

Chay lenh sau de tao audit report, khong sua `targets.csv`:

```powershell
py -3.12 scripts/audit_calibration_targets.py
```

Ket qua `WAITING_TARGET_DATA` la dung neu chua co target approved, hoac chua
du metadata va phan bo calibration/holdout. Chi khi report tra
`READY_FOR_CALIBRATION` moi du dieu kien chuyen sang buoc calibration.

## Hàng đợi phenotype candidate

Các giá trị mới trích từ paper nằm trong
[`../datasets/literature_phenotypes/phenotype_records.csv`](../datasets/literature_phenotypes/phenotype_records.csv).
Đây là hàng đợi review, không phải input calibration. Research lead chỉ chuyển
một record sang `targets.csv` khi paper registry, assay, statistic, uncertainty,
sample size và mục đích `calibration` hoặc `holdout` đã được duyệt độc lập.
