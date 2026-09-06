# Pipeline Steps 5–12 để xây dựng bài báo

Tài liệu này là luồng thực thi chuẩn cho hướng **neural-first computational locomotion**. Orchestrator tương ứng là `scripts/run_publication_pipeline.py`. Orchestrator mặc định chỉ đọc artifact và tạo gate report; không tự ý chạy GPU.

## Step 5: Healthy baseline

Healthy phải được chạy cùng physics, timestep, controller, thời lượng và seed protocol. `disease_layer_enabled=false`, calibration và holdout đều tắt. Gate chỉ đạt khi từng seed có metric đầy đủ, timestamp hợp lệ, contact, joint/action trajectory và không có NaN/Inf.

```powershell
py -3.12 scripts/run_publication_pipeline.py --prepare-branches
```

Lệnh này kiểm tra summary Gate 19 và tạo branch audit nhẹ; không chạy simulation. Nếu cần tái chạy baseline thật, dùng runner Gate 19 với cấu hình đã khóa và lưu raw artifact ngoài Git.

## Step 6: Disease multi-seed

Mỗi condition phải đi qua disease neural branch và checkpoint riêng. Condition thiếu mapping sẽ được ghi `WAITING_REVIEWED_MAPPING`. Không dùng action-level proxy cũ để gắn nhãn gene-specific. Mỗi seed cần manifest riêng, cùng physics và timestep với healthy.

Condition hiện có thể mở rộng:

- `alpha_synuclein`, `pink1`, `parkin`, `dj1`, `lrrk2`: chờ mapping neuron/edge có provenance;
- `dopamine_deficiency_exploratory`: class-level exploratory branch, không phải gene-specific.

Sau khi branch và perturbation đã sẵn sàng, chạy explicit từng seed bằng `scripts/run_brain_body_neural_first.py`. Không dùng một rollout smoke để gọi là multi-seed.

Khi đã có mapping hợp lệ, có thể chạy batch có resume:

```powershell
py -3.12 scripts/run_publication_pipeline.py `
  --execute-disease-rollouts `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python ..\drosophila-pd-flygym\.venv\Scripts\python.exe
```

Lệnh này giữ nguyên protocol 100.000 bước/seed trong config. Để kiểm tra nhẹ trên máy trước, truyền `--steps 1000`; kết quả đó chỉ là smoke run, không được gộp vào bảng multi-seed publication. Orchestrator tự bỏ qua seed đã có integration manifest PASS và ghi condition bị chặn thay vì tạo output giả.

## Step 7: Chen calibration

Chen là target calibration duy nhất trong protocol này. Chọn burden/parameter trên calibration data và khóa trước confirmation. Không dùng Pozo, không chọn lại sau holdout. Gate cũ của Chen được lưu như historical action-level reference; để gọi là neural-first calibration phải chạy lại trên disease neural-first multi-seed artifact.

## Step 8: Confirmation

Chạy lại parameter đã khóa bằng seed độc lập, không thay đổi burden hoặc objective. Kết quả phải phân loại rõ `CONFIRMED`, `NOT_REPRODUCED` hoặc `QUANTITATIVE_MISMATCH`.

## Step 9: Pozo holdout

Pozo chỉ được mở sau calibration/confirmation. Giữ `distance_traveled_mm` là distance, không đổi thành speed. Báo cáo direction, ratio, magnitude, mismatch và giới hạn assay. Không tuning theo Pozo.

## Step 10: Robustness

Bộ kiểm tra bắt buộc gồm nhiều seed, burden 0 và burden dương, sensitivity, negative control, QC contact/joint/action, checksum và tái lập. Mọi lỗi phải làm gate fail hoặc waiting; không bỏ qua để lấy figure đẹp.

## Step 11: Artifact package

Giữ `metrics.json`, `metrics.csv`, summary, manifest, checksum, figures, report và video đại diện. Raw rollout lớn có thể hash rồi xóa sau QC theo policy; không đưa checkpoint/connectome/PDF cục bộ/video lớn vào source Git.

## Step 12: Public package

Package công bố gồm manuscript, README tái lập, config, environment, source manifest, checksum, figures, tables và claim/limitation lock. `PUBLICATION_PACKAGE_PARTIAL` là trạng thái đúng khi neural-first disease multi-seed hoặc mapping gene-specific còn thiếu.

## Claim lock

Pipeline có thể hỗ trợ một bài về computational locomotion proxy và phương pháp ràng buộc bằng literature. Nó chưa tự động chứng minh biological Parkinson mechanism, gene-specific validation, chẩn đoán, đáp ứng thuốc hoặc thay thế thí nghiệm ruồi thật.
