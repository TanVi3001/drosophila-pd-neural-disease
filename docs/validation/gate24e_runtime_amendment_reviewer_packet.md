# Gate 24E-R1: Gói review runtime amendment

## Quyết định cần review

Hai reviewer độc lập cần xác nhận liệu commit memory-safe có chỉ thay đổi export và
post-processing sau simulation hay không. Chưa được chạy `attempt_03` trước khi review này
hoàn tất và auditor trả về trạng thái cho phép tương ứng.

> The scientific simulation semantics are unchanged. The amendment changes post-simulation artifact serialization and optional post-processing only.

## Runtime được so sánh

| Thuộc tính | Runtime gốc | Runtime amendment |
| --- | --- | --- |
| Commit | `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06` | `655e854544e3d814dfe422883ff0de66b619d6c1` |
| Profile | `LEGACY` | `GATE24E_MEMORY_SAFE` |
| Runner SHA256 | `6c27c6ca9421f3b358ed8ce17e8192be586b6777ce52c2201530ec713db03059` | `21b3854a2cf8e2087e143c0f7ccf97761b80c5eca3bda265d8e80729434d6b16` |
| Worktree mới | Không áp dụng | `../drosophila-pd-flygym-gate24-memorysafe-clean` |

Lý do amendment: `attempt_02` đã hoàn thành đủ `100000/100000` simulation steps nhưng
thất bại khi legacy exporter materialize full-frame JSON. Vì vậy số đo storage của lần đó
không hợp lệ và không có kết quả khoa học nào được chấp nhận.

## Hash source amendment

| Source | Git-blob SHA256 | Windows clean-worktree SHA256 |
| --- | --- | --- |
| Runner | `cea5c2489b62cd25324b42f1ca790258ced0bff9dd48cd391979aca3a91acfc1` | `21b3854a2cf8e2087e143c0f7ccf97761b80c5eca3bda265d8e80729434d6b16` |
| Memory-safe exporter | `82e47f98c919863e9bc5ae18db0d52e727b6fc4b4e3387b08ab6744d557543bc` | `0b79610f312bd2c282484814c123f5bf3c67fc655c3c4b0b66f9695243b4ebd2` |
| Memory-safe scalar analysis | `3f3e9dd9c04872adbc21418b26078e3f3ddca5712d34335fe60937e585d5274a` | `254079472a134dd501c3e1a0e27d45aa22ef9a250db0c921b5ae07118d2361fb` |

Hash simulation loop ở cả hai commit là
`d90d204826e1bda64197b74eecabf9cb96fe17eef3907df41bd79c7238223b5e`;
hash toàn bộ reviewed source diff là
`ecb460c6cdeba7916d35fe57439cdf4cc86859fbc1862dd49710ed4d107fd93a`.

Danh sách diff đầy đủ và phân loại từng file nằm trong
`docs/validation/gate24e_runtime_provenance_amendment_audit.md`. Hash máy đọc nằm trong
`experiments/gate_24e_storage_probe/manifests/runtime_amendment_checksums.json`.

- Runtime amendment SHA256:
  `d2fcb187dd5609169d52f7e499a0570a83bedc45b687d6c9b8fe3ab72790be0a`.
- Runtime checksum manifest SHA256:
  `f7ed628c75990ee4b8931b97a83505bf52c8610d6540c09d19bd657d339eb227`.

## Evidence kỹ thuật

- Clean worktree pin đúng commit `655e854544e3d814dfe422883ff0de66b619d6c1`.
- Thân simulation loop ở hai commit có cùng hash chuẩn hóa.
- NPZ legacy và NPZ memory-safe bằng nhau trên toàn bộ channel của fixture.
- Primary metric equivalence: `PASS`.
- Secondary metric equivalence: `PASS`.
- Memory regression: `PASS`.
- Test command chỉ dùng dữ liệu tổng hợp: `6 passed`; GPU `NO`; simulation `NO`.
- Gate 24D signoff gốc được tham chiếu bằng SHA256, không bị chỉnh sửa.

## Scientific invariants cần reviewer xác nhận

- Model commit `be4b10a80755d9f7bad931f56b8a739bd64e3619`.
- Mapping SHA256 `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`.
- 330-root target SHA256 `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`.
- Healthy checkpoint SHA256 `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`.
- Disease checkpoint grid, parameter grid `[0, 0.25, 0.5, 0.75, 1]` và seeds
  `[0, 1, 2, 3, 4]` không đổi.
- Neural transform SHA256 `8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b`.
- Physics `0.0001 s`, duration `10 s`, `100000` steps, controller và CPG không đổi.
- Primary/secondary metric và grid-level decision rule không đổi.

## Trạng thái an toàn hiện tại

| Gate | Trạng thái |
| --- | --- |
| Original Gate 24D | `PROSPECTIVE_PREDICTION_LOCKED` |
| Runtime amendment | `WAITING_GATE24E_RUNTIME_AMENDMENT_REVIEW` |
| Holdout | `SEALED` |
| Scientific jobs | `0/25` |
| `attempt_03` | `NOT_AUTHORIZED` |
| Scientific batch | `NOT_AUTHORIZED` |

## Cách reviewer ký

Reviewer phải tự đọc diff audit, checksum manifest và amendment YAML. Sau đó mới điền hai
tên người thật khác nhau, một ngày review ISO `YYYY-MM-DD`, và quyết định vào
`research/validation/prospective/parkin_runtime_amendment_reviewer_signoff.json`.

Không tái sử dụng tự động tên reviewer Gate 24D. Không dùng placeholder. Việc hai reviewer
chấp thuận amendment vẫn không tự động cho phép scientific batch; storage probe và quyền
batch phải có gate riêng.
