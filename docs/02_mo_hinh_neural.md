# Mô hình neural

Mô hình hiện tại được mô tả như một mạng neuron LIF/sparse connectome được
ghép với body FlyGym thông qua motor hoặc descending readout. Connectome mô
tả cấu trúc kết nối; nó không tự cung cấp cơ chế bệnh, trọng số sinh lý đầy đủ
hoặc bằng chứng rằng một neuron cụ thể đã mất trong genotype bệnh.

Perturbation được áp dụng theo edge có ID:

```text
W_disease[i,j,t] = W_healthy[i,j]
                       × presynaptic_gain[i,t]
                       × postsynaptic_gain[j,t]
                       × survival_mask[i,j,t]
```

Không dùng global weight scaling. Nếu không có mapping neuron/edge có nguồn,
condition phải dừng ở trạng thái chờ.

Các tham số hiện được coi là computational proxy:

- presynaptic gain;
- postsynaptic gain;
- neuron survival mask;
- energy capacity;
- energy consumption scale;
- noise;
- action delay.

Đây không phải mô phỏng dopamine, alpha-synuclein aggregation, ty thể ở cấp
phân tử hoặc chết tế bào thật.
