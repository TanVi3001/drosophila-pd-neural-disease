# Current Claim Lock

## Phạm vi

Đây là claim lock hiện hành sau Gate 14C. Mọi báo cáo, biểu đồ và bản thảo
phải tuân theo cách diễn giải này.

## Allowed project claim

This project implements a Chen-calibrated organism-level computational
locomotion proxy for Drosophila Parkinson-like locomotor phenotypes. The locked
proxy perturbation produced directional concordance in a Pozo PINK1 holdout
check, but did not quantitatively match the Pozo disease/control distance ratio.

## Cách viết tiếng Việt được phép

Dự án xây dựng một computational locomotion proxy ở mức organism-level cho kiểu
hình vận động Parkinson-like trên Drosophila. Tham số proxy được calibration
bằng Chen 2014 và được kiểm tra holdout bằng Pozo 2022. Kết quả holdout cho
thấy đúng chiều suy giảm vận động, nhưng chưa khớp định lượng với tỉ lệ
disease/control của Pozo.

## Forbidden wording

Không dùng các cách diễn đạt sau như một kết luận tích cực:

- biological Parkinson validation;
- gene-specific validation;
- clinical validation;
- drug validation;
- quantitatively validated holdout model;
- proven Parkinson disease mechanism;
- PINK1 biological model validated.

## Evidence table

| Gate | Evidence | Interpretation |
| --- | --- | --- |
| Gate 13B | Selected burden `0.5` | Chen-only calibration objective |
| Gate 13C | Confirmation ratio `0.6142` | Confirmation computational của burden đã khóa |
| Gate 14B | Simulated distance ratio `0.9470` | Directional concordance reported |
| Pozo 2022 | Target ratio `0.1920` | Holdout reference, không dùng để tune |
| Gate 14C | Ratio mismatch `0.7550` | Quantitative mismatch reported |

## Scientific boundary

Gate 14C không phải biological validation, không phải gene-specific PINK1 model
đã được xác nhận, không phải clinical prediction và không phải drug/therapeutic
validation.
