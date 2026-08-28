# Hợp đồng tích hợp với platform

Repository `drosophila-pd-flygym` là platform được pin theo tag hoặc commit.
Repository này không sửa source của platform.

## Đầu vào bắt buộc

- brain source có license rõ ràng;
- connectome đúng phiên bản;
- checkpoint healthy;
- neuron/edge annotation có provenance;
- FlyGym/MuJoCo runtime tương thích;
- calibration targets đã được review.

## Luồng đầu ra

Neural condition tạo edge artifact có manifest. Adapter brain-body sau này đọc
artifact đó, chạy mạng neural và gửi motor readout vào platform. Sau khi
rollout hoàn tất, platform tiếp tục tạo:

```text
rollout.json
rollout.npz
viewer_pose.json
metrics.json
biomarkers.json
```

Không được coi `perturbed_edges.npz` là rollout hoặc kết quả locomotion.

## Trạng thái hiện tại

Phần perturbation và calibration primitives đã có test độc lập. Adapter chạy
brain-body thật vẫn `WAITING_BRAIN_DATA` cho tới khi nguồn ngoài, annotation và
checkpoint được xác minh. Đây là blocker dữ liệu/pháp lý, không được giải quyết
bằng mock hoặc rollout giả.
