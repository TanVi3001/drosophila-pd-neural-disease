# Step 3: Neural Perturbation Runtime

## Mục đích

Step này materialize một checkpoint disease riêng từ checkpoint healthy đã khóa. Biến đổi được áp dụng trên connectome/checkpoint trước khi brain output đi vào controller; không scale action ở lớp cuối.

```text
healthy neural state
        |
        v
disease neural transform
        |
        v
perturbed neural activity
        |
        v
motor output
```

Các tham số được hỗ trợ trong schema hiện tại gồm presynaptic gain, postsynaptic gain, neuron survival, energy capacity, energy consumption scale, noise và action delay. Việc tham số hóa là computational proxy; giá trị không tự động trở thành giá trị sinh học đo được.

Chạy materializer:

```powershell
py -3.12 scripts/prepare_disease_neural_perturbation.py `
  --branch-manifest results/neural_branches/dopamine_deficiency_exploratory/branch_manifest.json `
  --brain-root external/fly-brain `
  --config configs/conditions/dopamine_deficiency.exploratory.yaml `
  --annotations annotations/neuron_annotations.csv `
  --age-days 5 `
  --brain-python ..\drosophila-pd-flygym\.venv\Scripts\python.exe `
  --output results/neural_perturbations/dopamine_deficiency_exploratory/day_005
```

Kết quả `DISEASE_NEURAL_PERTURBATION_READY` phải có hash checkpoint con khác checkpoint healthy và hash parent được kiểm tra lại. Checkpoint healthy chỉ được đọc; không copy hoặc ghi đè vào `external/fly-brain/data/plastic_weights.pt`.

Step này chưa chạy FlyGym, chưa calibration và chưa holdout validation.
