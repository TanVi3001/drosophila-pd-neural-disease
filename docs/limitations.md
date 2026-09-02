# Limitations

1. Đây là organism-level proxy, không phải mô hình cơ chế gene-specific.
2. Alpha-synuclein và PINK1 hiện được biểu diễn bằng computational proxy.
3. Simulation runtime được ghi nhận trong các gate hiện tại là khoảng `0.5 s`.
4. Chen calibration dùng ratio objective, không phải absolute assay-scale
   matching.
5. Pozo holdout đạt directionality nhưng chưa khớp quantitative ratio.
6. Pozo absolute distance chỉ có vai trò `reference-only` vì scale và thời
   lượng assay không được giả định tương đương trực tiếp với runtime.
7. Chưa có biological wet-lab validation.
8. Chưa có clinical hoặc drug validation.
9. Không được dùng kết quả để kết luận cơ chế bệnh Parkinson thật.
10. Parkin, DJ-1 và LRRK2 vẫn blocked nếu thiếu mapping/provenance đầy đủ.

## Hệ quả cho bài báo

Các kết quả nên được trình bày là computational locomotion evidence. Cần tách
rõ runtime pass, directional concordance và quantitative mismatch. Không gộp
chúng thành một tuyên bố biological validation.
