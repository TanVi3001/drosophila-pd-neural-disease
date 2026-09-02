# Gate 13C — Calibrated confirmation rerun

**Trạng thái:** `CHEN_CALIBRATED_CONFIRMATION_PASS`

## Phạm vi

Đây là confirmation rerun tính toán locomotion cho proxy alpha-synuclein ở scope organism-level. Gate này giữ khóa `proxy_burden_level=0.5` từ Gate 13B và dùng control burden `0.0` để kiểm tra lại bằng seed độc lập `6–11`.

Không chọn lại tham số, không tối ưu liên tục, không dùng Pozo/PINK1/holdout và không thực hiện gene-specific mapping. Đây không phải biological Parkinson validation, chẩn đoán, dự đoán lâm sàng, drug validation hay thay thế thí nghiệm wet-lab.

## Thiết kế thực thi

- Condition duy nhất: `alpha_synuclein`.
- Burden: `0.0` và khóa `0.5`.
- Seed: `6, 7, 8, 9, 10, 11` cho mỗi mức, tổng `12` rollout.
- Runtime: `5000` bước, timestep `0.0001 s`, thời lượng `0.5 s`, giữ nguyên physics/timestep/duration của Gate 11/12G.
- Rollout PASS: `12/12`.

## Kết quả đo

| Burden | Số run PASS | Mean planar speed (mm/s) | Ratio so với control | Sai số so với Chen | Độ trôi so với Gate 13B |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 6 | 1.9241723 ± 0.17419595 | NOT_REPORTED | NOT_REPORTED | NOT_REPORTED |
| 0.5 | 6 | 1.1818701 ± 0.12794442 | 0.61422258 | 0.055880514 | 0.028601392 |

## Ratio đối chiếu

- Chen reference ratio: `0.670103092783505`.
- Confirmation ratio (burden 0.5 / burden 0.0): `0.614222578419585`.
- Gate 13B selected ratio: `0.585621186102103`.
- CI95 của Chen được giữ nguyên là CI95; không chuyển thành SE.

## Blocker hoặc lỗi

- Không có blocker được ghi nhận.

## Artifact

Chỉ giữ metrics CSV/JSON, summary CSV, manifest, log và report. Rollout NPZ, video, viewer bundle và checkpoint không được commit; nếu được tạo trong quá trình chạy, chúng nằm trong thư mục tạm và bị xóa sau khi đo.

## Kết luận phạm vi

Gate 13C chỉ có thể được gọi là `CHEN_CALIBRATED_CONFIRMATION_PASS` theo QC rollout và operator. Nó không xác nhận cơ chế bệnh học, không phải biological Parkinson validation và không được dùng để suy ra hiệu quả thuốc.

## Trạng thái chuyển tiếp

`READY_FOR_GATE_14A_POZO_HOLDOUT_PROTOCOL` chỉ là trạng thái sẵn sàng lập protocol holdout sau confirmation; Gate 13C chưa chạy holdout và không sử dụng Pozo.
