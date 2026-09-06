# Step 4: Brain-to-Body Integration

## Mục đích

Step này đưa checkpoint neural disease riêng qua runner FlyGym/MuJoCo thật để kiểm tra chuỗi điều khiển hoàn chỉnh:

```text
Brain output
    -> controller.step()
    -> LocomotionAction
    -> apply_locomotion_action()
    -> simulation.step()
```

Chạy một rollout kiểm tra:

```powershell
py -3.12 scripts/run_brain_body_neural_first.py `
  --branch-manifest results/neural_branches/dopamine_deficiency_exploratory/branch_manifest.json `
  --perturbation-manifest results/neural_perturbations/dopamine_deficiency_exploratory/day_005/neural_perturbation_manifest.json `
  --brain-root external/fly-brain `
  --platform-root ..\drosophila-pd-flygym `
  --brain-python ..\drosophila-pd-flygym\.venv\Scripts\python.exe `
  --output results/neural_first_integration/dopamine_deficiency_exploratory_seed_000 `
  --seed 0 --steps 1000 --device cuda
```

Gate pass yêu cầu rollout có timestamp hữu hạn/tăng đều, `actuator_position` có shape `(frames, 42)` và trajectory không hằng, joint trajectory hữu hạn và contact có shape hợp lệ. Manifest cũng giữ bằng chứng parent healthy không đổi.

Có thể thêm `--video` hoặc `--video-output ...mp4` khi cần quan sát trực quan. Video là artifact của rollout tính toán, không phải bằng chứng bệnh học. Gate này cũng không tự tạo kết quả gene-specific hoặc biological Parkinson validation.
