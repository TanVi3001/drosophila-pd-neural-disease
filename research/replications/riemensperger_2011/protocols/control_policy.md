# Chính sách control cho tái lập Riemensperger 2011

`DTHg; ple` là **primary real control**. Đây là dòng cùng nền `ple` với
`DTHgFS±; ple` nhưng được rescue DTHg, nên phù hợp nhất với phép so sánh
matched disease/control trong Figure 2A.

`WT` (Canton S) chỉ là **secondary reference**. Dù paper báo cả WT, pipeline
không được thay `DTHg; ple` bằng WT khi tính effect ratio chính.

Endpoint chính là median walking speed:

```text
real_speed_ratio = median_speed(DTHgFS±; ple) / median_speed(DTHg; ple)
```

Với các số liệu được nêu trực tiếp trong paper, ratio này là `7.8 / 10.8`.
Không dùng variance chưa báo cáo để tạo error bar, và không đổi median thành
mean.
