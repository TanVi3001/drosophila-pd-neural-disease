# Báo cáo chạy và đánh giá kế hoạch nghiên cứu tháng 09/2026

Ngày thực hiện: 2026-09-15

Phạm vi: baseline computational brain model của Shiu et al. 2024, các artifact
FlyWire/MaleCNS mới đã clone, `drosophila-pd-neural`,
`drosophila-pd-neural-disease` và `drosophila-pd-flygym`.

## 1. Kết luận điều hành

Baseline 2024 đã chạy được trên máy Windows hiện tại với dữ liệu FlyWire
materialization 630. Tutorial `example.ipynb` đã execute thành công. Một thí
nghiệm đầy đủ gồm 30 trial x 1 giây với 21 sugar GRN cũng hoàn tất.

Healthy Baseline Metrics v1 đã được tạo từ parquet spike output, gồm tổng số
spike, firing rate, active neuron, biến thiên giữa trial, top responder và
provenance/checksum.

Kết quả này hoàn thành phần lõi của Tuần 1 và phần lớn Tuần 2-3. Tuy nhiên,
chưa thể gọi là bitwise reproduction của môi trường gốc vì máy không có
Conda/Python 3.10 và MSVC/Cython; lần chạy hiện tại dùng Python 3.12, Brian2
2.10.1 và NumPy code generation. Repo upstream cũng không đặt seed trong
`run_exp`, nên output stochastic không tái lập byte-for-byte.

Connectome mới đã cải thiện rõ lớp dữ liệu và provenance, nhưng chưa thay thế
baseline 2024 và chưa được nối trực tiếp vào FlyGym. MaleCNS v1.0, FlyWire
783 và FlyWire 630 là các dataset khác nhau; không được trộn edge hoặc
annotation nếu chưa có mapping và consumer contract.

## 2. Trạng thái từng deliverable

| Deliverable | Trạng thái | Bằng chứng |
|---|---|---|
| Clone repo baseline 2024 | PASS | `external/Drosophila_brain_model`, commit `91bdd1e7dcf193f3e7ca5a8933497fcef63b7960` |
| Setup Brian2 | PASS có giới hạn | Brian2 2.10.1 trong venv Python 3.12; fallback NumPy vì thiếu MSVC |
| Chạy `example.ipynb` | PASS | 19 cell sau khi bỏ cell Colab clone đã execute, gồm load output và rate analysis |
| Chạy baseline gốc release 630 | PASS | 30 trial x 1 giây, 21 sugar input, 1,238 giây |
| Hiểu input -> LIF -> spike output | PASS | Đã kiểm tra `model.py`, schema và parquet output |
| Hiểu neurotransmitter/excitatory flag | PASS một phần | Cờ `Excitatory` đã nằm trong connectivity 630; raw `top_nt` được đối chiếu qua FlyWire annotation 3.1.0 |
| Healthy Baseline Metrics v1 | PASS | `results/research_plan_20260915/healthy_baseline_metrics_v1.json` |
| Evaluator script | PASS | `scripts/evaluate_2024_baseline.py`, đã chạy trên 630, 783 và silencing output |
| Chạy một thí nghiệm 783 | PASS có kiểm soát | 20 ID giao nhau, 1 trial x 1 giây; không phải reproduction 630 |
| Kiểm tra activation + silencing | PASS kỹ thuật | Paired one-trial cùng seed Brian2; cần mở rộng nhiều trial để kết luận |
| Chạy canonical FlyGym healthy baseline | PASS | 5,000 bước, 0.5 giây, output riêng của platform |
| Chạy `figures.ipynb` full sweep | CHƯA CHẠY | Chi phí rất lớn; cấu hình Figure 1D đã được audit, một run tương ứng đã chạy qua API |
| Disease model từ connectome vào FlyGym | CHƯA CÓ consumer | Chỉ có action-level/bridge-scale adapter; chưa có neural checkpoint consumer |
| AI evaluation | CHƯA HOÀN THIỆN | Có thể tổng hợp/rank artifact; chưa được phép suy luận bệnh học hoặc tự duyệt claim |

## 3. Các repo và environment đã sử dụng

### 3.1 Baseline 2024

Repo: `https://github.com/philshiu/Drosophila_brain_model`

Commit đã pin: `91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`

Repo có:

- `model.py`: network LIF Brian2, activation, silencing và trial execution;
- `utils.py`: load spike parquet và tính rate;
- `example.ipynb`: tutorial activation/silencing;
- `figures.ipynb`: các sweep dùng cho figures;
- dữ liệu FlyWire release 630 và 783;
- output mẫu trong `results/example`.

Environment thực tế:

| Package | Version |
|---|---:|
| Python | 3.12.10 |
| Brian2 | 2.10.1 |
| NumPy | 2.5.3 |
| pandas | 3.0.5 |
| PyArrow | 25.0.1 |
| joblib | 1.6.0 |

Environment gốc trong `environment_full.yml` yêu cầu Python 3.10.11,
Brian2 2.5.1, NumPy 1.22.3, pandas 1.4.3 và PyArrow 11.0.0. Máy hiện tại
không có Python 3.10 hoặc Conda. Vì vậy trạng thái phù hợp là functional
reproduction, chưa phải exact environment reproduction.

Brian2 không tìm thấy Microsoft Visual C++ 14.0 nên báo không biên dịch được
Cython và fallback sang NumPy target. Điều này làm full run chậm; baseline
30 trial hoàn tất trong 1,238 giây.

### 3.2 Environment phân tích connectome mới

Đường dẫn: `D:\research\New folder\.venvs\connectome-analysis-312`

Đã cài và kiểm tra:

- `neuprint-python 0.6.3`;
- `navis 1.12.0` từ PyPI;
- `fafbseg 3.2.2`;
- `caveclient 8.2.1` và `cloud-volume 12.14.4`;
- `pandas`, `pyarrow`, `openpyxl`, `scipy`.

`pip check` đạt. NeuPrint client nhận đúng dataset `male-cns:v1.0` nhưng dừng
ở credential guard vì không có token. Không có token nào được ghi vào repo.

### 3.3 Environment runtime FlyGym

Đường dẫn: `D:\research\New folder\.venvs\flygym-runtime-312`

Đã cài:

- FlyGym 2.1.0;
- MuJoCo 3.9.0;
- matplotlib;
- editable install của platform và neural extension.

Canonical FlyGym baseline rerun đạt:

- 5,000 bước;
- timestep 0.0001 giây;
- duration 0.5 giây;
- planar displacement 6.284186 mm;
- mean planar speed 12.568372 mm/s;
- heading yaw change 0.234273 rad;
- 42 position actuator và 6 adhesion actuator;
- observations/derived metrics finite.

Đây là locomotion software baseline, không phải neural firing baseline và
không phải Parkinson validation.

## 4. Kiến trúc và cơ chế baseline 2024

Luồng dữ liệu thực tế:

```text
FlyWire completeness 630
        +
FlyWire connectivity 630
        +
neuron excitatory/inhibitory flag
        |
        v
Brian2 NeuronGroup: 127,400 neurons
        |
        +-- PoissonInput cho nhóm neuron được activate
        +-- Synapses với delay 1.8 ms
        +-- g/g_synaptic decay alpha-synapse
        +-- SpikeMonitor
        |
        v
spike parquet: t, trial, flywire_id, exp_name
        |
        v
firing rate / active neuron / downstream target response
```

### Tham số LIF đã xác nhận trong source

| Thành phần | Giá trị |
|---|---:|
| resting potential | -52 mV |
| reset potential | -52 mV |
| firing threshold | -45 mV |
| membrane time scale | 20 ms |
| synaptic decay tau | 5 ms |
| refractory period | 2.2 ms |
| synaptic delay | 1.8 ms |
| free synaptic weight | 0.275 mV |
| default Poisson input | 150 Hz |
| Poisson scale | 250 |

Connectivity weight trong code là `Excitatory x Connectivity` nhân với
`w_syn`. Neuron excitatory tạo depolarization, neuron inhibitory tạo
hyperpolarization. Baseline coi mỗi neuron là hoàn toàn excitatory hoặc hoàn
toàn inhibitory.

Các giới hạn cần ghi ngay trong note khoa học:

- zero basal firing;
- không có morphology, receptor dynamics hoặc gap junction;
- không có neuromodulation/neuropeptide;
- glutamate được mặc định là inhibitory;
- absolute firing rate không nên diễn giải như rate sinh lý tuyệt đối;
- mô hình phù hợp hơn cho directionality và so sánh condition trên một dải
  stimulation.

## 5. Kết quả chạy baseline 630

### Cấu hình

- dataset: FlyWire materialization 630;
- completeness: 127,400 neuron rows;
- connectivity: 14,687,178 connection rows;
- input: 21 labellar sugar GRN IDs;
- activation: 150 Hz Poisson input;
- trials: 30;
- duration: 1,000 ms mỗi trial;
- process: một CPU process để tránh nhân bản network lớn;
- output: `external/Drosophila_brain_model/results/reproduce_20260915/full_630/sugarR_original_630.parquet`.

### Healthy Baseline Metrics v1

| Metric | Kết quả |
|---|---:|
| total spikes | 407,460 |
| trials | 30 |
| active-neuron union | 432 |
| active neurons/trial mean | 375.867 |
| active neurons/trial SD | 6.213 |
| spikes/trial mean | 13,582 |
| spikes/trial SD | 293.220 |
| firing rate mean trên active-neuron union | 31.440 Hz |
| firing rate SD trên active-neuron union | 37.330 Hz |
| neurons rate >= 1 Hz | 364 |
| neurons rate >= 10 Hz | 268 |
| MN9 rate | 82.467 Hz |
| top responder rate | 153.633 Hz |
| finite/schema/provenance check | PASS |

Tất cả 21 declared sugar input ID đều xuất hiện trong output. 432 output IDs
đều có trong completeness 630. Connectivity audit xác nhận:

- 8,800,532 rows có weighted value dương;
- 5,886,646 rows có weighted value âm;
- 127,015 unique presynaptic IDs;
- 126,793 unique postsynaptic IDs.

### So với output mẫu trong repo

Output mẫu `results/example/sugarR.parquet` có 511,566 spikes, 448 active
neurons, 402.6 active neurons/trial và MN9 93.267 Hz. Fresh rerun có 407,460
spikes, 432 active neurons/trial union và MN9 82.467 Hz.

Chênh lệch này không nên được coi là lỗi sinh học ngay lập tức. Nguyên nhân
chính là upstream `run_exp` không đặt seed, Poisson input stochastic, và
environment hiện tại khác environment gốc. Kết luận hiện tại là:

- pipeline và schema reproduce được;
- magnitude/identity của downstream response vẫn hợp lý về mặt kỹ thuật;
- numerical reproduction chưa đạt mức exact;
- cần pin environment gốc và seed wrapper trước khi dùng sai số số học làm
  regression threshold.

## 6. Chạy `example.ipynb` và thí nghiệm perturbation

### Tutorial

Cell Colab clone đã được bỏ khi chạy local để không clone lồng repo. 19 cell
còn lại execute thành công. Tutorial đã:

- import `run_exp`, `default_params`, `utils`;
- load connectivity/completeness 630;
- đọc `sugarR.parquet`;
- tính rate và standard deviation;
- chạy path `sugarR_100Hz` theo cơ chế skip nếu output đã tồn tại;
- đọc rate MN9;
- đi qua nhánh top responder và silencing output mẫu.

Output tutorial mẫu cho MN9 ở `sugarR_100Hz` là khoảng 67.033 Hz.

### Paired activation/silencing one-trial

Đã chạy cùng process, reset NumPy/Brian2 seed 123 trước mỗi condition:

| Condition | Spikes | Active neurons | MN9 rate |
|---|---:|---:|---:|
| control | 13,736 | 377 | 89 Hz |
| silence top responder `720575940617000768` | 13,268 | 384 | 83 Hz |

Thay đổi quan sát được:

- MN9: -6 Hz, tương đương -6.74% trong one-trial paired test;
- tổng spike: -468;
- active-neuron union: +7.

Đây chỉ là engineering/scientific pilot, chưa đủ để kết luận neuron đó là
causal target. Cần tối thiểu nhiều trial, nhiều stimulation frequency và
control qua các target khác.

### Phát hiện quan trọng về semantics của silencing

README mô tả silencing là đặt zero các connection đến và đi khỏi neuron.
Implementation hiện tại trong `model.py` lọc biến synapse `i`, tức
presynaptic/source index, và đặt zero outgoing synaptic weight. Nó không
explicitly zero incoming weights hoặc PoissonInput của chính target neuron.

Vì vậy trong paired run, neuron bị “silence” vẫn có rate 147 Hz do nó vẫn
được external Poisson activation. Đây là điểm cần sửa hoặc ghi rõ trong
protocol trước khi dùng silencing làm disease intervention.

## 7. Kiểm tra chuyển release 630 sang 783

Repo cung cấp cả dữ liệu 630 và 783, nhưng paper 2024 dùng 630. Thử chạy cùng
21 sugar IDs với 783 thất bại ngay ở mapping:

```text
KeyError: 720575940620900446
```

ID này không có trong `Completeness_783.csv`. Với 20 ID còn lại, một trial x
1 giây chạy thành công:

| Metric | 630 fresh, 30 trial | 783, 20 ID, 1 trial |
|---|---:|---:|
| neurons in completeness | 127,400 | 138,639 |
| connectivity rows | 14,687,178 | 15,091,983 |
| input IDs | 21 | 20 |
| total spikes | 407,460 | 13,213 |
| active-neuron union | 432 | 374 |

Kết quả 783 chỉ chứng minh code có thể đọc schema 783 sau khi điều chỉnh input
set. Không được so sánh effect size với cột 630 vì release, input set và số
trial khác nhau.

## 8. Đối chiếu annotation và MaleCNS mới

`flywire_annotations` tag `v3.1.0` đã được pin ở commit
`8587524c1748ce5ef2080822a2fc890fc03bf597`.

Trong `Supplemental_file1_neuron_annotations.tsv`:

- 21/22 IDs gồm 20 sugar ID còn dùng được và MN9 được tìm thấy;
- tất cả 21 đều có `top_nt = acetylcholine`;
- 20 sugar ID là `flow = afferent`, `side = left`;
- MN9 là `flow = efferent`, `side = right`;
- tất cả 21 có `dimorphism = isomorphic`.

Trong `2025malecns/mcns_fw_edge_comp_mappings.json`:

- 21/22 IDs có cross-connectome label;
- 20 sugar IDs map thành `LB3`;
- MN9 map thành `CB0701`;
- ID thiếu của release 783 cũng không có trong mapping này.

Đây là cải thiện lớn so với baseline repo 2024: baseline chỉ dùng flag
`Excitatory` đã materialize trong edge table; artifact mới giữ thêm cell type,
flow, side, top neurotransmitter, dimorphism và mapping provenance. Tuy nhiên,
annotation FlyWire female và MaleCNS male vẫn phải giữ dataset namespace riêng.

Audit cross-edge MaleCNS/FlyWire đã có trong báo cáo repo connectome trước đó:
current catalog 360/360 ID khớp FlyWire annotation, 39/39 cell type có trong
crossmatch labels; đây là evidence cho intake/mapping chứ chưa phải neural
runtime.

## 9. So sánh với hệ thống hiện tại

### Điểm đã cải thiện

| Lớp | Baseline/system cũ | Sau khi cập nhật repo mới |
|---|---|---|
| neural simulation | LIF FlyWire 630, output spike/rate | Giữ nguyên baseline để reproduce; thêm evaluator và artifact 783 test |
| provenance | Nhiều file rời, chưa có unified audit | Commit/tag, dataset namespace, source checksum và manifest |
| annotation | Edge table chỉ có excitatory flag | FlyWire cell type, top NT, flow, side, dimorphism, crossmatch |
| connectome scope | Female FlyWire 630 | Có thêm FlyWire 783 và MaleCNS v1.0-derived comparison |
| connectivity audit | Không có male-female QC trong runtime baseline | Precision/recall, traced capture, edge verdict và mapping từ 2025malecns |
| morphology | Chưa có trong baseline runtime | `navis` offline skeleton/mesh smoke; `fafbseg` offline criteria smoke |
| query | Không có Python NeuPrint client | `neuprint-python` 0.6.3 sẵn sàng cho credentialed audit |
| locomotion | FlyGym baseline riêng | Có canonical healthy baseline + action-level/bridge-scale adapter |
| reproducibility | Notebook/manual output | Healthy Baseline Metrics v1 evaluator và JSON artifact |

### Điểm chưa cải thiện

- Chưa có synapse-level MaleCNS consumer trong Brian2 model.
- Chưa có mapping tự động, có confidence, từ MaleCNS body ID sang FlyWire
  630/783 ID cho mọi neuron.
- Chưa có neurotransmitter receptor dynamics hoặc morphology trong LIF.
- Chưa có neural spike-to-DN-to-CPG mapping được kiểm định.
- Chưa có đường `2024 spike parquet -> bridge_scales.json -> FlyGym`.
- Chưa có bệnh model từ alpha-synuclein/PINK1/DJ-1/complex-I được truyền qua
  neural dynamics thật.
- Chưa có AI model evaluation được calibrate bằng ground truth sinh học.

## 10. Mối quan hệ với FlyGym hiện tại

Hai baseline đang đo hai không gian khác nhau:

```text
Baseline 2024:
sensory GRN stimulation -> LIF graph -> spike/rate -> MN9/DN response

FlyGym hiện tại:
CPG controller -> 42 joint action + 6 adhesion -> MuJoCo -> locomotion metrics
```

Adapter hiện tại `BrainDrivenPerturbation` có thể nhận một
`bridge_scales.json` chứa `motor_scale`, `left_motor_scale`,
`right_motor_scale` và `coupling_scale`. Nó không đọc trực tiếp spike parquet
của Shiu model.

Do đó, các output cũ trong `drosophila-pd-flygym/results/brain_driven` không
được dùng như bằng chứng rằng connectome 2024 đã chạy trong runtime hiện tại.
Muốn nối hai hệ cần một consumer contract tối thiểu:

1. xác định target population và namespace ID;
2. chạy LIF baseline/disease cùng input và cùng seeds;
3. trích xuất DN/descending population rate;
4. định nghĩa hàm chuyển DN rate sang motor/coupling scale;
5. lưu scale artifact cùng checksum, config và mapping confidence;
6. gọi FlyGym paired baseline/perturbation;
7. chỉ sau đó mới tính delta locomotion.

## 11. Đánh giá pipeline bệnh và AI

### Pipeline nên giữ

```text
Healthy neural baseline
        |
        v
Target selection + annotation/provenance review
        |
        v
Neural perturbation: activation / silencing / edge weight condition
        |
        v
LIF simulation + spike/rate metrics
        |
        v
DN/readout adapter with explicit calibration
        |
        v
FlyGym paired rollout
        |
        v
Healthy vs condition comparison
        |
        v
AI report: summarize, rank, flag uncertainty, request human review
```

### AI được phép làm ở giai đoạn hiện tại

- tổng hợp metric JSON và provenance;
- so sánh paired condition;
- xếp hạng candidate theo tiêu chí đã pin;
- phát hiện missing schema/checksum/mapping;
- sinh report và danh sách câu hỏi cho giảng viên;
- gắn nhãn `WAITING_DATA`, `WAITING_MAPPING`, `WAITING_REVIEW`.

### AI chưa được phép làm

- tự gọi một spike change là Parkinson mechanism;
- tự đổi female FlyWire thành male MaleCNS;
- tự map neuron không có confidence/provenance;
- tự promote checkpoint thành rollout;
- tự quyết định target thực nghiệm;
- coi proxy burden hoặc motor scale là dopamine level/disease severity.

## 12. Các vấn đề cần hỏi giảng viên

1. Tháng này chọn track nào làm baseline chính: historical FlyWire 630 để
   reproduce paper, FlyWire 783 để cập nhật, hay MaleCNS v1.0 để xây model
   mới? Không nên dùng cả ba làm một baseline duy nhất.
2. Có chấp nhận functional reproduction trên Python 3.12/Brian2 2.10.1 hay
   cần dựng Linux/Conda exact environment Python 3.10/Brian2 2.5.1?
3. Khi nói silencing neuron, cần zero outgoing, incoming, cả neuron target,
   hay chỉ bỏ synaptic effect? README và source hiện chưa hoàn toàn nhất quán.
4. Readout nào sẽ được dùng để nối neural model vào locomotion: MN9, DN
   population, hay một scale được calibration riêng?
5. Có ground truth nào cho healthy neural firing và downstream motor response
   ngoài prediction từ paper không?
6. Disease intervention sẽ đặt ở neuron, synapse weight, neurotransmitter
   sign, hay motor bridge? Mỗi lựa chọn là một claim khác nhau.

## 13. Việc cần làm tiếp theo

### P0 — hoàn tất baseline reproducibility

- Dựng exact environment Python 3.10/Brian2 2.5.1 trong Linux/Conda nếu cần
  exact comparison.
- Thêm seed wrapper ngoài upstream repo; không sửa source upstream trực tiếp.
- Chạy lại `sugarR` 30 trial với exact environment.
- Chạy một control/silencing pair nhiều trial sau khi chốt semantics.
- Chạy một subset Figure 1D có lưu config, output và checksum.

### P1 — hoàn tất neural metrics và mapping

- Mở rộng evaluator thành rate matrix theo neuron x trial;
- thêm target group metadata và MN9/DN readout;
- tạo mapping table với các cột `source_dataset`, `source_id`,
  `target_dataset`, `target_id`, `mapping_method`, `confidence`, `evidence`;
- query NeuPrint cho một target set nhỏ sau khi có token;
- dùng navis để tạo figure audit skeleton/mesh cho target đã review.

### P2 — bridge sang locomotion

- định nghĩa contract cho DN rate -> bridge scale;
- xây một adapter thử nghiệm độc lập với disease claims;
- chạy paired FlyGym nhiều seed;
- sửa/quarantine lỗi `heading_rad` của short rollout;
- chỉ sau khi consumer chạy thật mới báo cáo locomotion effect của connectome.

## 14. Artifact và command tái chạy

Metrics artifact:

- `results/research_plan_20260915/healthy_baseline_metrics_v1.json`;
- `results/research_plan_20260915/healthy_baseline_metrics_783_one_trial.json`;
- `results/research_plan_20260915/healthy_baseline_metrics_silencing_630.json`;
- `scripts/evaluate_2024_baseline.py`.

Baseline 630:

```powershell
$py = ".venvs/baseline-2024-312/Scripts/python.exe"
& $py -c "from pathlib import Path; from model import run_exp, default_params; from brian2 import ms, Hz; ..."
```

Evaluator:

```powershell
& .venvs/baseline-2024-312/Scripts/python.exe `
  drosophila-pd-neural/scripts/evaluate_2024_baseline.py `
  --spikes external/Drosophila_brain_model/results/reproduce_20260915/full_630/sugarR_original_630.parquet `
  --output drosophila-pd-neural/results/research_plan_20260915/healthy_baseline_metrics_v1.json `
  --duration-s 1 `
  --completeness external/Drosophila_brain_model/2023_03_23_completeness_630_final.csv `
  --connectivity external/Drosophila_brain_model/2023_03_23_connectivity_630_final.parquet
```

FlyGym healthy baseline:

```powershell
& .venvs/flygym-runtime-312/Scripts/python.exe `
  drosophila-pd-flygym/scripts/run_healthy_baseline.py `
  --config drosophila-pd-flygym/configs/experiments/healthy_baseline.yaml `
  --output drosophila-pd-flygym/results/analysis/research_plan_20260915/healthy_baseline_rerun.json
```

## 15. Nguồn chính

- Shiu et al. 2024, Nature: https://www.nature.com/articles/s41586-024-07763-9
- Repo model: https://github.com/philshiu/Drosophila_brain_model
- Dorkenwald et al. 2024: https://www.nature.com/articles/s41586-024-07558-y
- FlyWire annotation: https://github.com/flyconnectome/flywire_annotations
- MaleCNS: https://male-cns.janelia.org/
- NeuPrint: https://neuprint.janelia.org/

## 16. Kết luận cuối

Mục tiêu ưu tiên “hiểu và reproduce baseline thật chắc” đã đạt ở mức
functional và có artifact định lượng. Nền tảng hiện tại đủ tốt để bắt đầu
mapping/readout review, nhưng chưa đủ để tuyên bố disease simulation chạy qua
toàn bộ chuỗi neural -> locomotion.

Bước đúng tiếp theo là khóa baseline 630 bằng exact environment/seed và chốt
semantics silencing. Sau đó mới dùng annotation FlyWire 783 và MaleCNS v1.0
như lớp provenance/cross-connectome, rồi xây bridge DN-to-CPG có calibration
và human review. Đây là đường ngắn nhất để các kết quả sau này có thể so sánh,
tái lập và giải thích được.
