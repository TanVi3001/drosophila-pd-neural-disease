# Gate 12D — Actual Proxy Disease Multi-Seed Rollouts

**Trạng thái:** `PROXY_DISEASE_ROLLOUTS_BLOCKED`

## Input status

- Gate 12C đã mở khóa `alpha_synuclein` và `pink1` ở scope `organism_level_proxy`.
- Gate 11 healthy baseline pass.
- Metric contract pass.
- Audit `READY_FOR_CALIBRATION`.

## Scope

Gate 12D chỉ dành cho computational proxy rollout. Không calibration, không holdout validation, không dùng Chen/Pozo để tune, không gene-specific mapping và không biological validation.

## Runtime

- Seeds: `0–5`.
- Step count: `5000`.
- Timestep: `0.0001 s`.
- Duration: khoảng `0.5 s`.
- Physics được khai báo giữ nguyên theo Gate 11.

## Proxy execution blocker

- `proxy_burden_to_action_operator_not_connected_to_current_brain_body_runner`

## Conditions

| Condition | Scope | Planned runs | Successful | Failed | Blocked | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `alpha_synuclein` | `organism_level_proxy` | 30 | 0 | 0 | 30 | `BLOCKED` |
| `pink1` | `organism_level_proxy` | 30 | 0 | 0 | 30 | `BLOCKED` |

## Metric summary

Chưa có metric disease thật: tất cả proxy run bị chặn trước simulation. Không tạo metric giả.

## Healthy comparison

Chưa thực hiện so sánh disease với Healthy vì chưa có proxy rollout PASS.

## Skipped conditions

- `parkin`: `BLOCKED_IN_GATE_12C`.
- `dj1`: `BLOCKED_IN_GATE_12C`.
- `lrrk2`: `BLOCKED_IN_GATE_12C`.

## Limitations

- Alpha-synuclein và PINK1 chỉ là organism-level computational proxy, không phải gene-specific mapping.
- Burden level dimensionless chưa phải calibration value và chưa được dùng để tune theo Chen/Pozo.
- Runtime hiện chưa chứng minh action-level operator kết nối burden proxy vào brain-body runner.
- Đây không phải biological Parkinson validation, clinical prediction, chẩn đoán hoặc drug validation.

## Final status

`PROXY_DISEASE_ROLLOUTS_BLOCKED`.
