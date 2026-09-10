# Generation 2 Research Charter

## Phạm vi

Generation 2 xây dựng một framework tính toán embodied có ràng buộc
connectome để đánh giá các giả thuyết vận động kiểu Parkinson ở
*Drosophila* bằng evidence sinh học đã công bố.

Repository hiện tại **chưa phải mô hình Parkinson sinh học hoàn chỉnh**.
Generation 2 kiểm tra liệu disease-specific latent state, neuromodulation,
cấu trúc circuit và assay-specific observation có tạo ra giá trị dự báo vượt
qua các proxy tính toán đơn giản hay không.

## Track được khóa

- Track đầu tiên: `RIEMENSPERGER_2011_DOPAMINE_FUNCTIONAL_DEFICIENCY`.
- Track tiếp theo: `ALPHA_SYN_DOPAMINE_PROGRESSION`.
- Flagship tương lai: `PINK1_SEROTONIN_DOPAMINE_MODEL_COMPARISON`.

Hai track sau chỉ là kế hoạch, chưa được bắt đầu ở Gate 28A.

## Nguyên tắc kiến trúc

```text
genotype / driver / age / intervention
    -> disease-specific latent state
    -> neuromodulation / cell state
    -> brain circuit
    -> descending / motor pathway
    -> body
    -> assay-specific observation
    -> study-level evaluation
```

Không dùng một scalar `Parkinson burden` chung cho nhiều cơ chế. Dopamine
functional deficiency, alpha-synuclein progression, PINK1 mitochondrial /
serotonergic state, Parkin/JNK và LRRK2 transport dysfunction phải là các
state hoặc plugin riêng khi được triển khai ở các gate sau.

## Ranh giới khoa học

Gate 28A chỉ khóa contract và dữ liệu mô tả. Không có GPU, simulation, model
fitting, calibration hoặc disease transform mới. Kết quả Generation 1,
bao gồm các kết quả âm tính, được giữ nguyên làm historical evidence và
baseline comparator.

## Lộ trình khóa

1. Gate 28A: scope, metric, duration, literature registry, study split.
2. Gate 28B: virtual assay adapter.
3. Gate 29: neural causal trace.
4. Gate 30: dopamine neuromodulation v1.
5. Gate 31: Riemensperger 2011 computational replication v2.
6. Gate 32: sensitivity, ablation, identifiability.
7. Gate 33: alpha-synuclein progression.
8. Gate 34: PINK1-serotonin flagship.
9. Gate 35: experiment-prioritization benchmark.

Chưa có gate sau 28A được đánh dấu đã thực thi.
