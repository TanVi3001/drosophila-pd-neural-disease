# Gate 09 Metric Review Checklist

Checklist này dùng cho review thủ công. Không đánh dấu hoàn tất khi chưa có
evidence từ PDF, figure, table hoặc supplementary.

## Reviewer identity

- [ ] Đã điền tên reviewer thật.
- [ ] Đã điền ngày review theo `YYYY-MM-DD`.
- [ ] Đã ghi rõ role/authority.

## Calibration target checklist

- [ ] Target được chọn rõ ràng.
- [ ] Metric là speed/velocity hoặc endpoint được policy cho phép.
- [ ] Value là số có provenance.
- [ ] Uncertainty là số có provenance.
- [ ] Uncertainty type giữ đúng theo paper.
- [ ] Sample size là số.
- [ ] Sample unit phản ánh đúng đơn vị phân tích.
- [ ] Phép đổi đơn vị có công thức vật lý rõ nếu có.
- [ ] Assay transfer được reviewer ghi `allowed`.
- [ ] Allocation là `calibration`.
- [ ] Provenance trỏ tới figure/table/supplement hoặc file digitization.
- [ ] Không đổi median thành mean.
- [ ] Không đổi CI95 thành SE khi chưa có policy riêng.

## Holdout target checklist

- [ ] Target được chọn rõ ràng.
- [ ] Metric holdout giữ đúng theo paper.
- [ ] Value là số.
- [ ] Spread/uncertainty là số và giữ đúng loại paper báo cáo.
- [ ] Sample size là số.
- [ ] Sample unit phản ánh đúng đơn vị phân tích.
- [ ] Assay transfer được reviewer ghi `allowed`.
- [ ] Allocation là `holdout`.
- [ ] Provenance rõ ràng.
- [ ] Holdout độc lập với calibration.
- [ ] Không dùng distance để calibration speed.
- [ ] Không đổi distance thành speed.
- [ ] Không đổi IQR/min-max thành SD hoặc SE.

## Audit readiness

- [ ] Có ít nhất một approved calibration target.
- [ ] Có ít nhất một approved holdout target.
- [ ] Approved rows có reviewer thật.
- [ ] Approved rows có review date thật.
- [ ] Approved rows có allocation.
- [ ] Approved rows có `assay_transfer=allowed`.
- [ ] Approved rows có sample unit.
- [ ] Approved rows có provenance.
- [ ] Audit trả `READY_FOR_CALIBRATION`.
