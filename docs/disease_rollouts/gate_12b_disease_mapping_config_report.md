# Gate 12B — Disease Condition Mapping and Burden Config Completion

## Mục tiêu

Gate 12B chuẩn bị cấu hình disease condition, mapping và provenance để Gate 12C có thể chạy rollout thật khi có đủ artifact. Gate này không tạo target khoa học và không chuyển condition sang `RUN_READY` nếu thiếu bằng chứng.

## Điều kiện cần để chạy thật

- Có `target_neurons` hoặc `target_edges` được xác nhận từ mapping có provenance.
- Có `burden_curve`, `full_burden` và đơn vị burden rõ ràng.
- Có literature source và mapping source.
- Có checkpoint source tương thích với runtime Gate 11 và checksum khi artifact có sẵn.
- Có reviewer và review date nếu condition được chuyển sang `RUN_READY`.

## Condition status

| Condition | Scope | Run status | Missing target | Missing burden | Missing provenance | Blocked reason |
| --- | --- | --- | --- | --- | --- | --- |
| `alpha_synuclein` | `not_ready` | `BLOCKED` | target neurons/edges | burden curve/full burden | mapping provenance, checkpoint compatibility | Pan-neuronal mapping chưa phải reviewed root-ID set cho disease condition. |
| `pink1` | `not_ready` | `BLOCKED` | target neurons/edges | burden curve/full burden | mapping provenance, checkpoint compatibility | Pink1B9 là organism-level mutant; chưa có model scope neural được duyệt. |
| `parkin` | `not_ready` | `BLOCKED` | target neurons/edges | burden curve/full burden | TH-GAL4 root-ID provenance, checkpoint compatibility | TH-GAL4 class scope chưa có reviewed root-ID set tương thích. |
| `dj1` | `not_ready` | `BLOCKED` | target neurons/edges | burden curve/full burden | cell-specific mapping, checkpoint compatibility | Literature hiện có climbing evidence nhưng không cung cấp intervention root-ID hợp lệ. |
| `lrrk2` | `not_ready` | `BLOCKED` | target neurons/edges | burden curve/full burden | VNC/motor-neuron provenance, checkpoint compatibility | Current connectome scope chưa đủ provenance cho motor-neuron/VNC condition. |

## Ý nghĩa của trạng thái BLOCKED

`BLOCKED` là trạng thái kiểm soát chất lượng, không phải kết quả disease. Gate 12B không chạy simulation, không chạy calibration và không chạy holdout validation. Không có metric disease nào được tạo trong gate này.

## Điều kiện chuyển sang RUN_READY

Reviewer phải cập nhật config tương ứng sau khi kiểm tra nguồn thật:

1. Ghi target neuron/edge hoặc scope class-level được phê duyệt.
2. Ghi burden curve, full burden, đơn vị và provenance.
3. Ghi checkpoint tương thích, checksum và manifest.
4. Ghi reviewer, review date và quyết định scope.
5. Chạy lại test/config audit trước Gate 12C.

Không được gọi condition là gene-specific nếu chỉ có tên gene, driver hoặc mapping class-level.

## Boundary

Đây là chuẩn bị computational disease perturbation cho locomotion. Nó không phải biological Parkinson validation, không phải chẩn đoán, clinical prediction, drug-response evidence hoặc thay thế thí nghiệm wet-lab.
