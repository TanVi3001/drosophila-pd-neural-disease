# Kiến trúc nghiên cứu

Repository này là lớp mở rộng nghiên cứu cho
`drosophila-pd-flygym`. Repository nền tảng cung cấp FlyGym, MuJoCo,
recorder, exporter, viewer, analysis và biomarker. Repository này chỉ cung cấp
condition neural, annotation, calibration và thí nghiệm GPU.

```text
Literature đã review
        ↓
Calibration targets
        ↓
Neuron/edge annotations
        ↓
Disease profile theo genotype và tuổi
        ↓
Neural perturbation
        ↓
Brain-body bridge
        ↓
FlyGym + MuJoCo
        ↓
Rollout / metrics / viewer
        ↓
Calibration và holdout validation
```

Không copy source hoặc checkpoint của `phase-A-clean` nếu chưa kiểm tra
license. Đường dẫn máy cá nhân không được coi là dependency tái lập được.
