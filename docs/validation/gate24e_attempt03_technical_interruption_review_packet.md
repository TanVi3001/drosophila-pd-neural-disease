# Gate 24E-S4A: Gói review gián đoạn kỹ thuật và xin quyền attempt_04

## Quyết định cần con người xem xét

Gói này chỉ đề nghị hai reviewer thật đánh giá việc cấp quyền cho **một**
technical storage probe mới có mã `attempt_04`. Task này không tự ký, không tạo
thư mục output `attempt_04`, không chạy GPU và không chạy simulation.

## Bằng chứng về attempt_03

`attempt_03` được khóa ở trạng thái
`STORAGE_PROBE_ATTEMPT_03_TECHNICAL_FAILURE`:

- Process đã vào simulation trên CUDA và có marker `20000/100000`,
  `40000/100000`.
- Process kết thúc bằng `KeyboardInterrupt` trong simulation.
- Không có marker hoàn tất `100000/100000`.
- `last_confirmed_progress_steps=40000` không phải số step thực thi chính xác;
  `exact_executed_steps_known=false`.
- `simulation_completed=false`, `storage_measurements_valid=false` và
  `storage_qualification_valid=false`.

Nguyên nhân sâu hơn của gián đoạn là
`UNRESOLVED_FROM_AVAILABLE_EVIDENCE`. Cách mô tả được phép là: "The process
terminated with KeyboardInterrupt during simulation." Không được suy đoán rằng
người dùng chủ động dừng, GPU/controller/model hỏng hoặc hệ điều hành kết thúc
process khi chưa có bằng chứng.

## Vì sao attempt_03 đã consumed

Quyền cũ chỉ áp dụng cho đúng một lần chạy `attempt_03`. Process đã khởi chạy
simulation nên quyền một lần đó đã được sử dụng, dù simulation chưa hoàn tất.
Do đó `attempt_03_consumed=true`, `attempt_03_retry_allowed=false`; không được
xóa artifact cũ rồi chạy lại dưới cùng authorization.

Storage measurements của attempt này không hợp lệ vì pipeline chưa đạt điểm
hoàn tất simulation và post-simulation export. Đây là technical interruption,
không phải scientific failure và không sinh scientific result để diễn giải.

## Vì sao cần authorization mới

Storage vẫn ở `GATE24E_STORAGE_NOT_QUALIFIED` với lý do
`NO_VALID_COMPLETED_STORAGE_PROBE`. Một probe mới chỉ hợp lệ khi hai reviewer
khác nhau xác nhận bằng chứng trên và cấp quyền riêng cho `attempt_04`. Việc ký
không cho phép tự động retry, không mở holdout và không cấp quyền cho batch 25
scientific jobs.

## Contract kỹ thuật bị khóa cho attempt_04

| Trường | Giá trị khóa |
|---|---|
| Attempt | `attempt_04` |
| Loại | `TECHNICAL_HEALTHY_STORAGE_PROBE` |
| Seed | `9001` (ngoài scientific seeds `0..4`) |
| Steps | `100000` |
| Duration | `10.0 s` |
| Device | `cuda` |
| Platform commit | `655e854544e3d814dfe422883ff0de66b619d6c1` |
| Artifact profile | `GATE24E_MEMORY_SAFE` |

Không được thêm `--prepared-checkpoint`, `--parameter`, `--video`,
`--compare-to` hoặc `--cpg-frequency-hz`; không đổi seed hay giảm steps.

## Scientific contract được giữ nguyên

| Thành phần | Giá trị khóa |
|---|---|
| Model commit | `be4b10a80755d9f7bad931f56b8a739bd64e3619` |
| Mapping SHA256 | `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80` |
| Target neuron SHA256 | `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085` |
| Target count | `330` |
| Healthy checkpoint SHA256 | `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691` |
| Parameter grid | `[0.0, 0.25, 0.5, 0.75, 1.0]` |
| Scientific seeds | `[0, 1, 2, 3, 4]` |
| Neural transform SHA256 | `8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b` |
| Timestep / duration | `0.0001 s` / `10.0 s` |
| CPG | `12.0 Hz` |
| Primary metric | `median_planar_speed_mm_s` |
| Secondary metric | `distance_traveled_mm` |

Decision rule, mapping, checkpoints, seeds, grid và analyzer không thay đổi.
Scientific jobs vẫn là `0/25`; scientific batch **không được cấp quyền**;
holdout vẫn `SEALED`.

## Câu hỏi bắt buộc cho reviewer

1. **A.** `attempt_03` có được phân loại đúng là technical interruption không?
2. **B.** Có bằng chứng nào cho thấy `attempt_03` tạo scientific result không?
   Kỳ vọng: **NO**.
3. **C.** Có bằng chứng nào cho thấy storage qualification đã đạt không?
   Kỳ vọng: **NO**.
4. **D.** Model, mapping, checkpoint, seeds, grid và decision rule có giữ nguyên
   không? Kỳ vọng: **YES**.
5. **E.** Một attempt kỹ thuật mới có hợp lý mà không thay scientific contract
   không? Reviewer phải tự quyết định **YES/NO**.

Nếu phê duyệt, hai người thật khác nhau phải điền signoff với ngày ISO
`YYYY-MM-DD`. Không được dùng tên placeholder.

## Claim boundary

> This authorization concerns only one new technical storage qualification
> attempt. It does not modify or validate the Parkin computational model and
> does not authorize biological or scientific interpretation.

Ranh giới claim khoa học vẫn là:

> Parkin-specific intervention represented by a reviewed driver-defined neural
> perturbation and a preregistered directional computational validation
> protocol; no biological validation claim.

Hành động hợp lệ tiếp theo duy nhất:
`HUMAN_REVIEW_GATE24E_ATTEMPT04_AUTHORIZATION`.
