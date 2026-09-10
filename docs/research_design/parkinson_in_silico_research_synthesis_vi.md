# Tổng hợp toàn diện hướng nghiên cứu Parkinson trên Drosophila in silico

## Thông tin tài liệu

- Ngày tổng hợp: 2026-09-10
- Phạm vi: repository `drosophila-pd-neural-disease`, các PDF đã cung cấp, các báo cáo và artifact hiện có trong repo
- Đối tượng đọc: thành viên sinh học, computational neuroscience, machine learning, simulation và reproducibility
- Ràng buộc thực tế: nhóm không có ruồi thật và không trực tiếp thực hiện wet-lab
- Nguồn kiểm chứng: dữ liệu ruồi thật đã công bố trong paper, supplementary và kho dữ liệu đi kèm
- Trạng thái khoa học hiện tại: organism-level computational locomotion proxy; chưa phải mô hình Parkinson sinh học hoàn chỉnh

Tài liệu này được viết để một teammate mới có thể hiểu toàn bộ dự án mà không cần đọc lại lịch sử trao đổi. Khi lấy số liệu vào calibration hoặc manuscript, vẫn phải quay lại paper gốc, figure/table gốc và metadata đã review.

---

## 1. Tóm tắt điều hành

### 1.1 Repository đã có giá trị gì?

Repo đã có nền kỹ thuật đáng kể:

- connectome não ruồi dạng sparse;
- neural runtime kiểu LIF;
- cầu nối brain-body;
- FlyGym/MuJoCo cho hình thái và vật lý;
- healthy rollout thật qua nhiều seed;
- kiểm soát chất lượng, manifest, checksum và provenance;
- disease perturbation pipeline;
- calibration, holdout và claim-adjudication pipeline;
- cơ chế chặn việc suy diễn root ID từ tên gene;
- tài liệu giới hạn claim tương đối nghiêm ngặt.

Đây là nền tốt để xây nghiên cứu computational. Tuy nhiên, disease layer hiện vẫn chủ yếu là proxy. Nó chưa trực tiếp mô phỏng:

- dopamine release và receptor-dependent neuromodulation;
- serotonin và SERT;
- alpha-synuclein aggregation;
- mitochondrial dysfunction;
- JNK/FOXO/apoptosis;
- microtubule và axonal transport;
- degeneration theo tuổi;
- VNC, motor neuron và muscle physiology đầy đủ.

### 1.2 Hướng nghiên cứu tối ưu

Không nên tiếp tục theo kiến trúc:

```text
tên gene -> một burden scalar -> giảm action -> giảm speed
```

Nên chuyển sang:

```text
genotype + driver + tuổi + can thiệp
                 -> disease-state module riêng
                 -> neuromodulator/cell state
                 -> brain circuit
                 -> descending neurons
                 -> VNC/CPG/motor neurons
                 -> body
                 -> assay-specific observation
```

Chương trình nên có hai tầng:

1. **Paper đầu tiên: alpha-synuclein -> dopamine circuit -> locomotor progression.**
   Đây là hướng phù hợp nhất với repo hiện tại và có chuỗi bằng chứng đầy đủ nhất.

2. **Flagship tiếp theo: PINK1 -> serotonin/SERT sớm -> dopamine circuit muộn -> locomotor phenotype.**
   Đây là hướng có độ mới sinh học cao nhất, nhưng cần thêm neuromodulation và aging state.

### 1.3 Mức claim cao nhất khi không có ruồi thật

Nếu hoàn thiện tốt, nhóm có thể tuyên bố:

> Xây dựng một framework Drosophila in silico bị ràng buộc bởi connectome, cơ sinh học và nhiều nghiên cứu độc lập; framework có khả năng kiểm tra ngoài mẫu một tập phenotype Parkinson-like đã định nghĩa, so sánh các giả thuyết cơ chế và ưu tiên thí nghiệm cho phòng lab.

Nhóm chưa thể tuyên bố:

- ruồi mô phỏng tương đương ruồi thật;
- mô hình thay thế được wet-lab;
- đã chứng minh cơ chế Parkinson;
- đã xác nhận gene hoặc thuốc;
- có giá trị chẩn đoán hay dự đoán lâm sàng.

---

## 2. Câu hỏi nghiên cứu trung tâm

### 2.1 Câu hỏi chính

> Một mô hình brain-VNC-body-assay bị ràng buộc bởi connectome có thể giải thích và dự đoán ngoài mẫu các phenotype vận động phụ thuộc tuổi, circuit, genotype và assay trong các mô hình Parkinson-like ở Drosophila hay không?

Câu hỏi này chia thành ba lớp:

1. **Tái hiện:** mô hình có tạo đúng xu hướng và effect size đã công bố không?
2. **Khái quát hóa:** tham số học từ một nhóm paper có dự đoán được paper, lab hoặc assay chưa dùng để fit không?
3. **Phân biệt cơ chế:** dữ liệu hiện có có phân biệt được neuromodulator dysfunction, neuron loss, motor-circuit failure và body/controller failure không?

### 2.2 Không có wet-lab thì vẫn làm được gì?

Nhóm vẫn có thể làm:

- retrospective external validation;
- leave-one-study-out validation;
- cross-assay model comparison;
- Bayesian inference và uncertainty propagation;
- sensitivity và identifiability analysis;
- xây benchmark dữ liệu mở;
- mô phỏng counterfactual trong phạm vi đã hiệu chỉnh;
- xếp hạng thí nghiệm có expected information gain cao cho lab bên ngoài.

Nhóm không thể tự đạt:

- prospective biological validation;
- kiểm tra mù một dự đoán hoàn toàn mới;
- xác nhận một quan hệ nhân quả mới;
- chứng minh chuyển giao sang một lab mới;
- xác nhận hiệu lực hoặc độc tính của thuốc.

Vì vậy, sức nặng khoa học phải đến từ thiết kế validation, khả năng khái quát hóa, uncertainty, identifiability và tính tái lập, không phải từ cách gọi "virtual fly hoàn chỉnh".

---

## 3. Thang bằng chứng và thuật ngữ

### 3.1 Các mức bằng chứng

| Mức | Ý nghĩa | Ví dụ | Có phải validation sinh học không? |
| --- | --- | --- | --- |
| L0 | Runtime verification | Rollout chạy đủ frame, không NaN, có movement | Không |
| L1 | Computational consistency | Perturbation làm thay đổi output mô phỏng | Không |
| L2 | Retrospective concordance | Mô phỏng cùng chiều hoặc gần effect size paper | Không |
| L3 | External computational validation | Dự đoán paper/study đã giữ ngoài quá trình fit | Không, nhưng là validation computational mạnh |
| L4 | Prospective biological validation | Lab mới kiểm tra dự đoán đã khóa | Có thể, nếu thiết kế đủ mạnh |

Mục tiêu khả thi của nhóm là L3. Không có wet-lab, nhóm không tự đạt L4.

### 3.2 Cách dùng thuật ngữ

- `runtime PASS`: code và artifact đạt kiểm tra kỹ thuật.
- `directional concordance`: đúng hướng tăng/giảm.
- `quantitative concordance`: effect size nằm trong tiêu chí định trước.
- `external computational validation`: study giữ ngoài toàn bộ quá trình fit.
- `surrogate`: mô hình thay thế cho một endpoint và miền điều kiện cụ thể.
- `digital twin`: chưa phù hợp vì chưa có cá thể cụ thể, cập nhật dữ liệu và xác thực lặp lại.
- `Parkinson-like locomotion model`: phù hợp hơn `Parkinson biological model` ở hiện tại.

---

## 4. Đánh giá repository hiện tại

### 4.1 Thành phần đã hoàn thiện

Theo các artifact đã ghi nhận, healthy protocol sử dụng:

- FlyWire FAFB v783;
- source commit được pin;
- sparse neural graph gồm 138,639 neuron và 15,091,983 synapse;
- 18/18 descending neurons được ánh xạ trong brain-body bridge;
- FlyGym 2.1.0 và MuJoCo 3.9.0;
- 5 healthy seed;
- 5,000 bước mỗi rollout;
- timestep 0.0001 giây;
- tổng thời gian mô phỏng 0.5 giây;
- neural execution trên CUDA trong protocol đã khóa.

Kiểm tra chất lượng bao gồm:

- frame count và timestamp;
- NaN/Inf;
- thorax movement;
- path length và speed;
- foot contact;
- joint movement;
- quaternion;
- observation/actuator state;
- manifest, kích thước file và SHA256;
- phát hiện rollout trùng giữa các seed.

Healthy baseline đã ghi 81 kiểm tra `PASS`, 0 `FAIL` và 5 `WARN` do chưa export raw action command.

Tài liệu liên quan:

- [`docs/healthy_baseline_methods_and_evidence.md`](../../docs/healthy_baseline_methods_and_evidence.md)
- [`configs/healthy_baseline_reproducible.yaml`](../../configs/healthy_baseline_reproducible.yaml)
- [`data/SOURCE_PROVENANCE.md`](../../data/SOURCE_PROVENANCE.md)

### 4.2 Ý nghĩa đúng của healthy baseline

Healthy baseline chứng minh:

- neural-body runtime chạy được;
- simulator tạo locomotion;
- artifact có thể truy vết;
- pipeline có thể làm chuẩn kỹ thuật cho disease condition.

Nó không chứng minh:

- neural dynamics tương đương ruồi thật;
- speed mô phỏng khớp một assay sinh học cụ thể;
- circuit khỏe mạnh đã được biological validation;
- cùng controller sẽ phản ứng đúng khi mắc bệnh.

Các bootstrap CI qua 5 seed chỉ mô tả biến thiên kỹ thuật. Chúng không phải biological uncertainty.

### 4.3 Disease layer đang có

Neural perturbation được mô tả dạng:

```text
W_disease[i,j,t]
  = W_healthy[i,j]
  * presynaptic_gain[i,t]
  * postsynaptic_gain[j,t]
  * survival_mask[i,j,t]
```

Ngoài ra còn có các operator:

- energy capacity;
- energy consumption scale;
- noise;
- action delay;
- action-level attenuation.

Đây là tham số tính toán. Chúng không tự động bằng:

- nồng độ dopamine;
- alpha-synuclein burden sinh học;
- tỷ lệ ty thể hỏng;
- JNK activity;
- neuron-death percentage;
- liều thuốc.

### 4.4 Kết quả disease rollout hiện tại

#### Alpha-synuclein và PINK1 proxy

Trong Gate 12G, alpha-synuclein và PINK1 sử dụng cùng action-level proxy nên cho cùng dãy kết quả. Response không đơn điệu: burden từ 0 đến 0.75 thường làm giảm speed, nhưng burden 1.0 lại làm speed tăng mạnh.

Diễn giải đúng:

- perturbation hook hoạt động;
- response có thể là artifact của controller/body interaction;
- chưa có cơ chế alpha-syn hoặc PINK1 riêng;
- burden không phải biological disease severity.

#### Parkin proxy

Gate 21 và Gate 22 chạy thành công về kỹ thuật. Tuy nhiên, burden không tạo quan hệ dose-response rõ trên speed, distance và displacement. Thay đổi nhỏ, có lúc đổi chiều.

Diễn giải đúng:

- Parkin pipeline execution đạt QC;
- Parkin phenotype reproduction chưa đạt;
- mapping chỉ là dopaminergic class-level exploratory;
- không có gene-specific Parkin validation.

#### PINK1/Pozo holdout

| Đại lượng | Giá trị |
| --- | ---: |
| Simulated control distance | 1.66678981 mm |
| Simulated disease-proxy distance | 1.57846176 mm |
| Simulated disease/control ratio | 0.94700709 |
| Pozo target ratio | 0.19203838 |
| Absolute ratio mismatch | 0.75496871 |

Mô hình đúng chiều giảm nhưng sai định lượng lớn. Đây là negative result có giá trị: một generic action attenuation được hiệu chỉnh ở source khác không chuyển giao tốt sang PINK1/Pozo.

Tài liệu liên quan:

- [`docs/disease_rollouts/gate_12g_integrated_proxy_rollout_report.md`](../../docs/disease_rollouts/gate_12g_integrated_proxy_rollout_report.md)
- [`docs/disease_rollouts/gate_22_parkin_healthy_comparison_report.md`](../../docs/disease_rollouts/gate_22_parkin_healthy_comparison_report.md)
- [`docs/holdout/gate_23_pozo_holdout_validation_report.md`](../../docs/holdout/gate_23_pozo_holdout_validation_report.md)

### 4.5 Mapping readiness

Hiện chưa có gene-specific mapping được duyệt đầy đủ cho năm condition chính:

| Condition | Vấn đề |
| --- | --- |
| alpha-synuclein | Pan-neuronal hoặc circuit driver chưa phải reviewed FlyWire root-ID set |
| PINK1 | Whole-animal mutant không tự động map thành một tập neuron |
| Parkin | TH-GAL4/class evidence chưa phải gene-specific root IDs |
| DJ-1 | Molecular/behavioral paper không cung cấp root-ID mapping |
| LRRK2 | D42 motor-neuron/VNC scope không tương thích brain-only mapping hiện tại |

Dopamine deficiency có 342 dopamine-class IDs, nhưng condition vẫn được ghi đúng là class-level exploratory.

Tài liệu liên quan:

- [`research/disease_mapping/disease_condition_readiness.csv`](../disease_mapping/disease_condition_readiness.csv)
- [`docs/disease_rollouts/gene_specific_mapping_handoff_vi.md`](../../docs/disease_rollouts/gene_specific_mapping_handoff_vi.md)

### 4.6 Kết luận audit

Mô tả chính xác nhất cho repo hiện tại là:

> Reproducible connectome-to-body locomotion platform có disease proxy và literature-evaluation pipeline.

Mô tả chưa chính xác là:

> Bộ não và toàn bộ hệ thần kinh ruồi Parkinson đã được phục dựng hoàn thiện trên máy tính.

---

## 5. Ma trận toàn bộ tài liệu nghiên cứu

| Nguồn | Hệ sinh học | Endpoint chính | Giá trị cho repo | Vai trò đề xuất |
| --- | --- | --- | --- | --- |
| Riemensperger 2011 | Neural dopamine deficiency | Speed, distance, activity | Tách functional deficiency khỏi neuron loss | Dopamine unit test |
| Riemensperger 2013 | alpha-syn trong dopamine pathway | Progressive locomotor deficit | Disease-circuit anchor mạnh | External circuit validation |
| Pokrzywa 2017 | Pan-neuronal human alpha-syn | Longitudinal speed/distance/activity | Nhiều tuổi và intervention | Progression calibration candidate |
| Haywood 2004 | alpha-syn + Parkin | Climbing, lifespan | Rescue có chọn lọc | Intervention holdout |
| Aggarwal 2019 | PD locomotor assay | Speed, distance, gait, geotaxis | Chuẩn hóa assay và metric | Assay contract |
| Dimitrescu 2023 supplement | Parkin RNAi | Dopamine release/TH theo vùng và tuổi | Ràng buộc spatial neuromodulation | Auxiliary mechanism constraint |
| Cha 2005 | Parkin/JNK | TH/DA morphology, locomotion, rescue | Molecular causal chain | Future JNK module |
| Liu 2008 | LRRK2 WT/G2019S | Age-related locomotion, DA loss | Variant/cell-specific evidence | Future degeneration module |
| Godena 2014 | LRRK2 R1441C/Y1699C | Axonal transport, climbing, flight | Intracellular mechanism mạnh | Separate project |
| Hwang 2013 | DJ-1/DLP/dFOXO/JNK | Stress survival, DA death, climbing | Genotype x stress mechanism | Future stress module |
| PINK1-serotonin 2022 | Pink1B9, 5-HT/SERT | HPLC, SERT, arena, PPL1/PPL2 | Novelty và temporal structure cao | Flagship challenge |
| Poddighe 2014 | Pink1B9 + Mucuna/L-DOPA | Climbing, olfaction, lifespan | Nhiều hypothesis nhưng source risk | Context only |
| Liessem 2026 | Dopamine và walking direction | Forward/backward/turning | Functional circuit constraint | Direction module |
| Pugliese 2025/2026 | VNC connectome/CPG | Leg coordination | Motor architecture | Implementation hypothesis |
| NeuroMechFly v2 2024 | Whole-body biomechanics | Embodied locomotion | Body/physics platform | Shared embodiment layer |
| Cha 2005 OA | Trùng Cha 2005 | Trùng | Không phải replication độc lập | Deduplicate |

---

## 6. Phân tích từng paper

### 6.1 Riemensperger et al. 2011: dopamine deficiency

Nguồn:

- `SOURCE_REGISTERED_EXTERNALLY: riemensperger_2011_dopamine_deficiency.pdf`
- <https://pubmed.ncbi.nlm.nih.gov/21187381/>

#### Thiết kế và kết quả quan trọng

- Tạo neural dopamine deficiency trong khi dopamine neurons vẫn tồn tại về giải phẫu.
- Ruồi trưởng thành 2-5 ngày tuổi, flight-disabled, được theo dõi từng cá thể trong open arena 15 phút.
- Walking speed báo cáo dạng median:
  - dopamine-deficient: 7.8 mm/s;
  - genetic rescue/control liên quan: 10.8 mm/s;
  - WT: 15 mm/s.
- Distance trong 15 phút cũng báo cáo median:
  - dopamine-deficient: 193 cm;
  - rescue/control: 425 cm;
  - WT: 474 cm.

#### Ý nghĩa

Functional dopamine deficiency có thể gây locomotor deficit trước hoặc không cần neuron loss. Vì vậy, mô hình phải tách:

```text
dopamine function/release != dopamine neuron survival
```

#### Cách áp dụng

- Unit test cho dopamine neuromodulation layer.
- Kiểm tra functional loss riêng với survival loss.
- Hỗ trợ median-aware likelihood.
- Không dùng trực tiếp làm target cho `mean_planar_speed_mm_s`.
- Cần virtual open-arena 15 phút hoặc observation model tương ứng.

### 6.2 Riemensperger et al. 2013: alpha-synuclein progression

PDF: [`riemensperger_2013_alpha_synuclein_progression.pdf`](../../aggarwal_2019_pd_locomotor_assay/riemensperger_2013_alpha_synuclein_progression.pdf)

#### Kết quả quan trọng

- alpha-syn liên quan progressive locomotor deficit.
- Một dopamine pathway PAM nhỏ được liên hệ với phenotype.
- Sử dụng startle-induced negative geotaxis và circuit/driver-specific manipulation.

#### Giá trị

- Disease-circuit anchor tốt nhất trong tập paper.
- Buộc mô hình phải có circuit specificity thay vì giảm toàn bộ dopamine system.
- Có thể làm external validation cho mô hình học từ pan-neuronal alpha-syn.

#### Giới hạn

- Driver expression không tự động chuyển thành FlyWire root IDs.
- SING/climbing không phải planar speed.
- Một pathway giải thích một phenotype không có nghĩa mọi alpha-syn phenotype đều đi qua pathway đó.

### 6.3 Pokrzywa et al. 2017: alpha-syn FlyTracker theo tuổi

PDF: [`pokrzywa_2017_alpha_syn_flytracker.pdf`](../literature_papers/open_access/pokrzywa_2017_alpha_syn_flytracker.pdf)

#### Protocol

- Pan-neuronal human WT alpha-syn qua nSyb-GAL4.
- Female flies; 20 độ C khi phát triển, 29 độ C sau eclosion.
- 10 ruồi mỗi vial, 3-10 vial mỗi treatment.
- Vial được tap ba lần; ghi 10 giây ở 30 fps.
- Tuổi: ngày 1, 7, 16, 21, 30 và 42.
- Metric: mean/max speed, walking duration, distance, percent moving, trajectory length và movement episodes.

#### Kết quả

- alpha-syn có suy giảm vận động tiến triển.
- Mean speed xấp xỉ 5.6 -> 2.5 mm/s trong ba tuần đầu; control xấp xỉ 6 -> 5 mm/s.
- Detection có threshold, nên movement quá chậm có thể bị xem như không di chuyển.
- MS400 amyloid inhibitor cải thiện nhiều kinetic metric và lifespan.
- L-DOPA cải thiện một số kinetic endpoint nhưng làm xấu lifespan trong điều kiện paper.
- FN075 có early hyperactivity và late impairment.

#### Cách áp dụng

- Calibration candidate tốt nhất cho alpha-syn age trajectory.
- Xây observation model có detection threshold.
- Fit đa endpoint, không chỉ mean speed.
- Tách symptomatic rescue khỏi disease reversal.

#### Giới hạn

- Experimental unit gồm flies, vials và repeated sequences.
- Error bars cần digitization và review.
- Một số biochemical measurement có cỡ mẫu hạn chế.
- Không tự chứng minh DA neuron death là nguyên nhân duy nhất của behavior.

### 6.4 Haywood et al. 2004: Parkin rescue alpha-syn

PDF: [`haywood_2004_parkin_alpha_synuclein_climbing.pdf`](../../aggarwal_2019_pd_locomotor_assay/haywood_2004_parkin_alpha_synuclein_climbing.pdf)

#### Kết quả chính

- Parkin overexpression có thể rescue alpha-syn-related climbing phenotype.
- Rescue locomotion không đồng nghĩa rescue mọi phenotype như lifespan.

#### Cách áp dụng

- Held-out intervention-specificity test.
- Mô hình phải cho phép cải thiện motor output mà latent disease state không nhất thiết trở về healthy.
- Cần virtual climbing assay hoặc study-specific observation model.

### 6.5 Aggarwal et al. 2019: locomotor assay và gait

PDF: [`aggarwal_2019_pd_locomotor_assay.pdf`](../../aggarwal_2019_pd_locomotor_assay/aggarwal_2019_pd_locomotor_assay.pdf)

#### Nội dung có ích

- Rotating vertical locomotor assay.
- Ruồi trưởng thành khoảng 3-5 ngày; observation khoảng 5 phút.
- Endpoint gồm track count, duration, distance, speed, straightness, geotactic index, gait concurrency, swing và stance.

#### Cách áp dụng

- Xây metric contract.
- Xây virtual assay tương ứng.
- Mở phenotype space từ speed/distance sang gait, straightness và geotaxis.
- Không dùng paper này để suy ra molecular mechanism.

### 6.6 Dimitrescu et al. 2023 supplement: Parkin RNAi và dopamine release

PDF: [`dimitrescu_2023_parkin_rnai_supplement.pdf`](../../aggarwal_2019_pd_locomotor_assay/dimitrescu_2023_parkin_rnai_supplement.pdf)

#### Nội dung có ích

- Parkin RNAi ảnh hưởng evoked dopamine release theo tuổi và vùng.
- Central complex và mushroom body không phản ứng giống nhau.
- FSCV và TH cho phép phân biệt functional release với neuron/protein state.

#### Cách áp dụng

- Ràng buộc spatial dopamine model.
- Không giảm đồng nhất mọi dopamine neuron.
- Dùng như auxiliary endpoint, không chuyển thành speed.

#### Giới hạn

- Region-level evidence chưa phải root-ID parameter.
- Không có phép biến đổi xác thực trực tiếp từ FSCV sang synaptic gain.

### 6.7 Cha et al. 2005: Parkin và JNK

PDF:

- [`cha_2005_parkin_jnk_dopaminergic.pdf`](../../aggarwal_2019_pd_locomotor_assay/cha_2005_parkin_jnk_dopaminergic.pdf)
- [`cha_2005_parkin_jnk_dopaminergic_oa.pdf`](../../aggarwal_2019_pd_locomotor_assay/cha_2005_parkin_jnk_dopaminergic_oa.pdf)

Hai file có cùng SHA256 và phải tính là một source, không phải hai nghiên cứu độc lập.

#### Kết quả chính

- Parkin loss liên quan JNK activation.
- Có thay đổi TH/dopamine-neuron morphology và locomotion.
- L-DOPA có symptomatic rescue trong protocol.

#### Cách áp dụng

- Source cho future Parkin/JNK module.
- Có thể kết hợp DJ-1 paper để xây shared stress-JNK-cell-health abstraction.

#### Giới hạn

Repo chưa có signaling, apoptosis hay dopamine synthesis. Không nên thay toàn bộ chuỗi sinh học bằng một presynaptic-gain scalar rồi gọi đó là JNK mechanism.

### 6.8 Liu et al. 2008: LRRK2 Parkinsonism

PDF: [`liu_2008_lrrk2_parkinsonism.pdf`](../../aggarwal_2019_pd_locomotor_assay/liu_2008_lrrk2_parkinsonism.pdf)

#### Kết quả chính

- Human LRRK2 WT/G2019S được biểu hiện trong Drosophila.
- Có age-related locomotor deficits, survival effects và selective DA-neuron changes ở các group như PPL1/PPM1/2.
- L-DOPA có symptomatic effect.

#### Cách áp dụng

- Variant-specific DA-degeneration benchmark trong tương lai.
- Ràng buộc tuổi và cell-group specificity.

#### Giới hạn

Không được gộp G2019S với Roc-COR variants của Godena thành một generic `LRRK2 burden`. Mutation, driver, cell type và mechanism khác nhau.

### 6.9 Godena et al. 2014: LRRK2, microtubule và axonal transport

PDF: [`godena_2014_lrrk2_microtubule.pdf`](../literature_papers/open_access/godena_2014_lrrk2_microtubule.pdf)

#### Kết quả chính

- LRRK2 R1441C/Y1699C ưu tiên liên kết deacetylated microtubules.
- Làm rối loạn vận chuyển ty thể hai chiều theo sợi trục.
- Trong Drosophila motor neurons với D42-GAL4, R1441C/Y1699C làm giảm transport, climbing và flight.
- HDAC6/Sirt2 knockdown và TSA tăng tubulin acetylation, rescue transport và locomotion.

#### Cách áp dụng

- Causal chain mạnh từ intracellular process đến behavior.
- Phù hợp một dự án multiscale riêng: microtubule -> axonal transport -> motor-neuron function -> behavior.

#### Giới hạn

- Repo thiếu microtubule, mitochondrial particles, axonal geometry và VNC/motor-neuron mapping.
- Climbing/flight assay chưa có.
- Đây là expansion lớn, không phải patch nhỏ cho paper alpha-syn.

### 6.10 Hwang et al. 2013: DJ-1, DLP, dFOXO và stress

PDF: [`hwang_2013_dj1_dlp.pdf`](../literature_papers/open_access/hwang_2013_dj1_dlp.pdf)

#### Kết quả chính

- DJ-1b mutants có thể không có gross DA loss trong điều kiện bình thường.
- Dưới oxidative stress, DA-neuron loss và apoptosis tăng.
- Chuỗi được đề xuất: DJ-1 loss -> Akt giảm -> dFOXO tăng -> DLP tăng -> JNK/dFOXO pro-apoptotic loop.
- DLP deficiency rescue stress sensitivity, DA-neuron death và climbing.
- Climbing dùng 10 male flies, acclimation 1 giờ, tap xuống đáy, đếm ruồi lên trên trong 4 giây, 10 trial/group và nhiều independent repeats.

#### Cách áp dụng

- Genotype x environment disease module.
- Future oxidative-stress/JNK validation.
- Không dùng một DJ-1 scalar bất chấp environment.

### 6.11 PINK1-serotonin 2022: rối loạn monoamine sớm

PDF: [`pozo_2022_pink1_serotonin.pdf`](../literature_papers/open_access/pozo_2022_pink1_serotonin.pdf)

PubMed: <https://pubmed.ncbi.nlm.nih.gov/35563850/>

File trong repo được đặt tên `pozo_2022`; trước manuscript cần chuẩn hóa author metadata theo bài gốc. Tựa bài đã đăng ký là *An Early Disturbance in Serotonergic Neurotransmission Contributes to the Onset of Parkinsonian Phenotypes in Drosophila melanogaster*.

#### Protocol và kết quả

- Male Pink1B9.
- HPLC 5-HT tại các cửa sổ tuổi 0-3, 7-10, 14-17, 21-24 và 28-31 ngày.
- Pink1 giảm 5-HT rõ ở 7-10 và 14-17 ngày.
- Chưa thấy serotonergic-neuron count hoặc Trh-protein change tương ứng tại thời điểm sớm được đánh giá.
- SERT activity giảm ở ngày 14 dù expression không nhất thiết giảm.
- Fluoxetine 15 micromolar được cho từ ngày 3-6 rồi dừng.
- Single fly circular arena 39 mm x 2 mm, 3 phút, phân tích bằng CeTrAn.
- Ngày 28, untreated control distance khoảng 323.326 mm; Pink1 khoảng 62.091 mm.
- Activity time control khoảng 51.894 giây; Pink1 khoảng 11.865 giây.
- Early fluoxetine cải thiện Pink1 nhưng gây bất lợi trên control.
- Protection khác nhau giữa PPL1 và PPL2; PPL2 được bảo vệ trong Pink1 nhưng có thể bị hại trong control.
- Genetic SerT perturbation trong Pink1 background cũng rescue behavior.

#### Vì sao đây là flagship tốt?

Paper tạo bài toán có:

- early functional dysfunction trước cell loss;
- multiscale temporal structure;
- nonlinear response;
- genotype-dependent intervention;
- cell-group specificity;
- motor endpoint muộn;
- nhiều giả thuyết cơ chế có thể so sánh.

#### Cách áp dụng khi không có ruồi thật

- Mechanistic model comparison, không phải causal proof.
- Out-of-distribution challenge sau alpha-syn model.
- Giữ toàn paper làm holdout trong ít nhất một fold.
- Nếu dùng một số endpoint để fit thì endpoint còn lại chỉ là within-study prediction, không phải independent-study validation.

### 6.12 Poddighe et al. 2014: Pink1B9 và Mucuna/L-DOPA

PDF: [`poddighe_2014_pink1b9_climbing.pdf`](../../aggarwal_2019_pd_locomotor_assay/poddighe_2014_pink1b9_climbing.pdf)

Expression of Concern: <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0231371>

#### Giá trị còn có thể dùng

- Gợi ý liên hệ giữa Pink1B9, climbing, olfaction, lifespan, mitochondria, BRP/TH và intervention.

#### Quy tắc sử dụng

- Chỉ dùng để sinh hypothesis hoặc tìm source khác.
- Không dùng làm primary calibration target.
- Không dùng làm decisive holdout.
- Mọi target lấy từ đây phải có source-risk flag.

### 6.13 Liessem et al. 2026: dopamine và hướng đi bộ

PDF: [`liessem_2026_walking_direction_dopamine.pdf`](../../aggarwal_2019_pd_locomotor_assay/liessem_2026_walking_direction_dopamine.pdf)

PubMed: <https://pubmed.ncbi.nlm.nih.gov/42442357/>

#### Giá trị chính

- Các dopamine population có vai trò khác nhau với forward walking, backward walking và ipsiversive turning.
- MDNs liên quan backward walking; các population khác liên quan forward/turning trong protocol paper.

#### Cách áp dụng

- Ràng buộc direction-specific motor policy.
- Mở endpoint sang turning, heading và locomotor-mode transitions.
- Phân biệt giảm movement amplitude với sai action selection.

#### Giới hạn

- Đây không phải paper Parkinson.
- Connectome không tự biểu diễn dopamine volume transmission.
- Receptor effect không thể suy ra chỉ từ edge list.

### 6.14 Pugliese et al. 2025/2026 preprint: VNC CPG

PDF: [`pugliese_2025_fly_cpg_preprint.pdf`](../../aggarwal_2019_pd_locomotor_assay/pugliese_2025_fly_cpg_preprint.pdf)

PubMed record: <https://pubmed.ncbi.nlm.nih.gov/42094485/>

#### Giá trị chính

- Dynamic VNC-connectome và minimal-CPG hypothesis.
- Đề xuất cấu trúc nhỏ inhibitory/excitatory cho coordination.
- Có prediction về DNb08 nối với optogenetic validation trong preprint.
- So sánh qua nhiều connectome giúp đánh giá robustness.

#### Cách áp dụng

- Blueprint cho descending -> VNC/CPG -> leg coordination.
- Giảm phụ thuộc vào black-box mapping từ 18 descending neurons sang 42 joint commands.

#### Giới hạn

- Vẫn là preprint tại thời điểm tổng hợp.
- Không phải disease evidence.
- Không nên xem minimal CPG là toàn bộ motor controller đã xác nhận.

### 6.15 NeuroMechFly v2 2024: body và sensorimotor platform

PDF: [`neuromechfly_v2_2024.pdf`](../../aggarwal_2019_pd_locomotor_assay/neuromechfly_v2_2024.pdf)

#### Giá trị chính

- Whole-body morphology và mechanics.
- Contact, proprioception và sensorimotor interfaces.
- Nền cho embodiment và virtual assay.

#### Cách áp dụng

- Shared body/physics layer cho mọi disease module.
- Phân biệt neural failure với mechanical/controller failure.

#### Giới hạn

- Không phải Parkinson model.
- Body fidelity không bảo đảm disease/neural fidelity.
- Khớp metric vật lý không tự chứng minh cơ chế thần kinh.

---

## 7. Kết luận xuyên paper

### 7.1 Không tồn tại một `Parkinson burden` chung hợp lệ

Các paper mô tả ít nhất bốn loại state khác nhau:

1. **Neuromodulator functional deficiency khi neuron còn tồn tại**
   - Riemensperger 2011;
   - early PINK1-serotonin;
   - regional dopamine release của Dimitrescu.

2. **Protein/age-dependent circuit dysfunction**
   - Riemensperger 2013;
   - Pokrzywa longitudinal alpha-syn.

3. **Stress signaling và degeneration**
   - Parkin/JNK;
   - DJ-1/DLP/dFOXO;
   - PPL1/PPL2 loss.

4. **Intracellular transport và mitochondrial mechanics**
   - LRRK2 microtubule/transport;
   - PINK1/Parkin mitochondrial context.

Một scalar có thể fit một endpoint nhưng không nhận dạng được cơ chế và thường không khái quát qua gene, driver hoặc assay.

### 7.2 Phải tách hai thang thời gian

```text
Slow disease state:
age, aggregation, mitochondria, signaling, cell survival
được cập nhật theo ngày/tuần

Fast embodied state:
neural activity, neuromodulation, CPG, body movement
được cập nhật theo millisecond/second
```

Không cần chạy LIF liên tục trong 30 ngày. Có thể dùng:

1. slow-state model cập nhật tham số tại các mốc tuổi;
2. fast embodied rollout tại từng mốc;
3. assay observation model để tạo endpoint tương ứng.

### 7.3 Connectome không đủ để mô phỏng dopamine

Dopamine có thể tác động qua:

- volume transmission;
- receptor expression;
- tonic/phasic release;
- presynaptic và postsynaptic modulation;
- plasticity;
- cell-state dependence.

Do đó, `top_nt=dopamine` cộng với edge list không tạo ra một dopamine-function model đã xác thực.

### 7.4 Behavior không xác định duy nhất mechanism

Cùng một giảm speed có thể do:

- dopamine release giảm;
- action selection thay đổi;
- motor-neuron drive giảm;
- CPG coordination hỏng;
- muscle/energy suy giảm;
- pause tăng;
- assay threshold.

Đây là identifiability gap, không chỉ là gap về tên gọi. Đọc thêm paper chỉ giải quyết được nếu paper có measurement hoặc perturbation phân biệt các cơ chế.

### 7.5 Rescue behavior không bằng disease reversal

L-DOPA hoặc một operator tăng motor output có thể cải thiện speed mà không:

- loại alpha-syn;
- phục hồi mitochondria;
- ngăn neuron death;
- phục hồi lifespan;
- loại toxicity/trade-off.

Mô hình phải tách symptomatic state khỏi disease state.

---

## 8. Phân loại các gap

### 8.1 Gap về tên gọi và claim

Có thể sửa ngay:

- `virtual brain complete` -> `connectome-constrained neural runtime`;
- `Parkinson model` -> `Parkinson-like locomotion proxy` khi chưa có mechanism;
- `validation` -> `retrospective computational concordance` khi phù hợp;
- tách `PASS runtime` khỏi `PASS scientific hypothesis`;
- ghi rõ burden là dimensionless proxy.

### 8.2 Gap kỹ thuật có thể xây bằng công nghệ hiện tại

- virtual assay adapters;
- rollout dài hơn;
- VNC/CPG layer;
- dopamine neuromodulation;
- serotonin/SERT model;
- age/disease-state model;
- cell-survival state;
- hierarchical observation model;
- literature digitization registry;
- leave-one-study-out evaluation;
- uncertainty, sensitivity và identifiability tooling.

### 8.3 Gap có thể lập trình nhưng dữ liệu chưa xác định đủ tham số

- receptor-specific dopamine gains;
- alpha-syn load -> release dysfunction mapping;
- mitochondria -> neural excitability mapping;
- JNK -> cell-death hazard;
- early serotonin -> later PPL2 protection.

Có thể xây phương trình cho các quan hệ này, nhưng không được coi một bộ tham số fit từ behavior là biological truth. Cần priors, parameter ensembles và uncertainty.

### 8.4 Gap không thể loại bỏ chỉ bằng dữ liệu hiện có

- xác nhận causal direction mới;
- xác nhận một intervention/time window chưa từng đo;
- chứng minh transfer sang lab mới;
- chứng minh virtual fly thay thế live fly;
- xác nhận drug efficacy/toxicity;
- phân biệt mechanisms tạo cùng endpoint nếu không có perturbation phân biệt.

Những gap này phải được báo cáo, không che giấu. Một identifiability result tốt vẫn là đóng góp khoa học.

---

## 9. Xếp hạng hướng nghiên cứu

Điểm 1-5 dưới đây là đánh giá chiến lược, không phải kết quả thống kê.

| Hướng | Fit repo | Evidence chain | Longitudinal/intervention | Novelty | Development risk | Quyết định |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| alpha-syn PAM/DA -> locomotion | 5 | 4 | 5 | 4 | 3 | Paper đầu tiên |
| PINK1 5-HT/SERT -> DA -> locomotion | 3 | 4 | 5 | 5 | 4 | Flagship tiếp theo |
| Parkin/JNK | 2 | 4 | 3 | 3 | 5 | Module sau |
| LRRK2 axonal transport | 1-2 | 5 | 3 | 4 | 5 | Dự án riêng |
| DJ-1 oxidative stress | 1-2 | 5 | 2 | 3 | 5 | Module sau |
| Generic multi-gene burden | 2 | 1 | 2 | 1 | 5 | Không làm |

---

## 10. Paper alpha-syn/dopamine đề xuất

### 10.1 Working title

*An uncertainty-aware connectome-constrained embodied model of progressive alpha-synuclein locomotor dysfunction in Drosophila*

### 10.2 Câu hỏi

Một latent alpha-syn/dopamine-circuit model có thể giải thích age trajectory và khái quát qua các driver, assay và lab độc lập không?

### 10.3 Vai trò dữ liệu đề xuất

| Source | Vai trò ban đầu |
| --- | --- |
| Riemensperger 2011 | Dopamine functional-deficiency unit test; median-aware |
| Pokrzywa 2017 | Primary longitudinal calibration candidate |
| Riemensperger 2013 | Circuit/driver generalization |
| Haywood 2004 | Intervention-specificity holdout |
| Aggarwal 2019 | Assay/gait phenotype validation |
| Dimitrescu 2023 | Regional/age dopamine constraint |
| Liessem 2026 | Direction-specific circuit prior |
| Pugliese + NeuroMechFly | Motor/body implementation, không phải disease target |

Allocation cuối cùng phải khóa trước fit. Tốt nhất chạy leave-one-study-out thay vì chỉ có một split.

### 10.4 Đóng góp IT

- multiscale disease-to-behavior model;
- connectome-constrained latent perturbation;
- assay-specific observation models;
- hierarchical cross-study inference;
- held-out posterior prediction;
- identifiability và failure analysis;
- reproducible benchmark.

### 10.5 Đóng góp sinh học hợp lệ

- đánh giá dạng dopamine/circuit dysfunction nào phù hợp với nhiều phenotype đã công bố;
- phân biệt functional deficiency với structural loss;
- xác định prediction nào robust qua driver/assay;
- chỉ ra thí nghiệm nào có khả năng phân biệt mechanisms.

### 10.6 Claim có thể dùng

> Mô hình connectome-constrained tái hiện và khái quát hóa một tập phenotype alpha-syn locomotor progression trên nhiều nghiên cứu đã công bố, với uncertainty và domain limits được định lượng.

Không dùng:

> Mô hình đã tái tạo hoàn chỉnh Parkinson hoặc thay thế ruồi thật.

---

## 11. Flagship PINK1-serotonin đề xuất

### 11.1 Working title

*Model comparison of early serotonergic dysfunction and later dopaminergic locomotor failure in Pink1B9 Drosophila*

### 11.2 Các giả thuyết cần so sánh

- H1: motor deficit chỉ do dopamine-neuron loss.
- H2: 5-HT/SERT dysfunction sớm điều biến dopamine circuit về sau.
- H3: mitochondrial decline gây song song 5-HT và DA dysfunction.
- H4: fluoxetine chỉ thay đổi motor expression, không bảo vệ disease state.
- H5: fluoxetine có nonlinear effect phụ thuộc genotype và cell state.

### 11.3 Endpoint cần giải thích đồng thời

- 5-HT theo tuổi;
- SERT kinetics;
- serotonergic-neuron/Trh state;
- PPL1 count;
- PPL2 count;
- distance;
- activity time;
- fluoxetine effect trên control và Pink1;
- genetic SerT perturbation.

### 11.4 Claim phù hợp

> Trong candidate model set, mô hình có early serotonergic state cho predictive adequacy tốt hơn trên dữ liệu đã công bố.

### 11.5 Claim không phù hợp

> Serotonin đã được chứng minh là nguyên nhân gây dopamine degeneration trong Pink1.

Không có prospective intervention mới, model comparison chỉ cho biết giả thuyết nào giải thích dữ liệu hiện có tốt hơn trong tập giả thuyết đã xét.

---

## 12. Kiến trúc phần mềm và mô hình mục tiêu

### 12.1 Sơ đồ tổng thể

```text
Genotype / driver / age / intervention / environment
                         |
                         v
              Disease-specific slow state
                         |
          +--------------+---------------+
          |                              |
          v                              v
  neuromodulator state          cell/energy/survival state
  DA, 5-HT, SERT, receptor      mito, stress, aggregation
          |                              |
          +--------------+---------------+
                         v
              Brain-circuit dynamics
                         v
              Descending populations
                         v
                VNC / CPG / MN layer
                         v
                 Body / environment
                         v
             Assay observation model
                         v
    speed, distance, bouts, turn, gait, climbing
```

### 12.2 Shared core

- connectome loader;
- neural dynamics;
- descending interface;
- VNC/CPG;
- body physics;
- assay layer;
- statistical inference;
- provenance và artifact contracts.

### 12.3 Disease plugins

#### alpha-syn

- progression/load state;
- presynaptic functional state;
- PAM/selected-DA population function;
- optional survival state;
- symptomatic intervention state.

#### PINK1

- mitochondrial health;
- 5-HT synthesis/release;
- SERT clearance;
- PPL1 function/survival;
- PPL2 function/survival;
- nonlinear fluoxetine/SerT intervention.

#### Parkin/DJ-1

- oxidative stress;
- abstract Akt/dFOXO/DLP/JNK state;
- dopamine function;
- cell-death hazard;
- environment interaction.

#### LRRK2

- mutation identity;
- microtubule acetylation;
- mitochondrial transport;
- axonal energy delivery;
- motor-neuron function;
- HDAC6/Sirt2/TSA intervention.

Paper đầu không cần xây mọi plugin, nhưng interface phải tránh quay lại generic burden.

### 12.4 Dopamine layer tối thiểu

Không nên dùng duy nhất:

```text
all dopamine neurons -> presynaptic_gain = 0.15
```

Cần tối thiểu:

```text
DA release theo population và tuổi
    -> extracellular/volume signal
    -> receptor/target-class modulation
    -> excitability, gain hoặc plasticity change
```

Tham số chưa biết phải có prior/range và uncertainty.

### 12.5 Assay layer bắt buộc

Mỗi assay config cần:

- geometry;
- vertical/gravity orientation;
- stimulus;
- individual hay group;
- duration;
- frame rate;
- movement threshold;
- exclusion rule;
- endpoint definition;
- aggregation statistic;
- experimental unit.

Ví dụ:

- Pokrzywa: group vial, 10 giây, 30 fps, threshold.
- PINK1-serotonin: single fly, circular arena, 3 phút.
- Riemensperger 2011: individual flight-disabled fly, 15 phút.
- Hwang: negative geotaxis, 4 giây success window.
- Aggarwal: rotating vertical assay, 5 phút, gait metrics.

---

## 13. Xây literature dataset đúng chuẩn

### 13.1 Một endpoint record phải có

- paper ID;
- figure/table/page;
- genotype;
- driver;
- sex;
- age;
- temperature;
- intervention dose/window;
- assay và duration;
- metric và unit;
- center statistic;
- spread statistic;
- sample size;
- experimental unit;
- digitization method;
- reviewer;
- source hash;
- role: prior/calibration/validation/context;
- source-risk flag.

### 13.2 Quy tắc digitization

- Ưu tiên raw data và supplementary table.
- Nếu chỉ có figure, lưu image hash, axis calibration và point provenance.
- Hai reviewer độc lập cho target quan trọng.
- Báo cáo digitization uncertainty.
- Không đọc tâm cột bằng mắt rồi ghi thành exact number.
- Không suy ra SD từ SE khi sample unit không rõ.
- Không ép median/IQR thành mean/SD nếu không khai báo distributional assumption.

### 13.3 Hệ phân cấp nguồn

| Mức | Nguồn | Cách dùng |
| --- | --- | --- |
| A | Raw data chính chủ + protocol rõ | Calibration/holdout tốt nhất |
| B | Numeric table/supplement | Calibration/holdout |
| C | Figure digitization + uncertainty | Có thể dùng với sensitivity |
| D | Text trend không có spread | Directionality/context |
| E | Source có concern hoặc metadata mơ hồ | Hypothesis only |

Poddighe ở mức E. Pugliese phải có preprint flag. Hai bản Cha chỉ tính một source.

### 13.4 Data leakage cần tránh

- Dùng Pozo để chọn model rồi tiếp tục gọi Pozo là holdout.
- Xem holdout, chỉnh burden, rồi báo cáo lại cùng target.
- Dùng hai endpoint cùng cohort như hai independent validations.
- Chọn threshold sau khi thấy test result.
- Digitize lại nhiều lần cho đến khi khớp mô hình.

Cần lưu split manifest, timestamp, source hash, model version và predeclared metrics.

---

## 14. Thiết kế calibration và validation

### 14.1 Leave-one-study-out

Với N study:

```text
Fold 1: train 2..N, test 1
Fold 2: train 1,3..N, test 2
...
Fold N: train 1..N-1, test N
```

Đây là thiết kế mạnh nhất khi không có dữ liệu mới vì nó kiểm tra chuyển giao qua paper, lab, driver và assay.

### 14.2 Hierarchical observation model

Không đồng nhất mọi assay. Nên mô hình hóa:

```text
latent motor state(age, genotype)
    -> assay transform
    -> lab/study effect
    -> measurement threshold
    -> observed endpoint
```

### 14.3 Metric đánh giá

Không chỉ dùng một disease/control ratio. Cần báo cáo:

- direction accuracy;
- relative/absolute effect error;
- standardized-effect error;
- RMSE/MAE;
- age-trajectory correlation;
- onset-time error;
- posterior-predictive interval coverage;
- held-out log predictive density;
- intervention-rank correlation;
- phenotype-profile similarity;
- failure cases.

Ngưỡng thành công phải khóa trước final holdout.

### 14.4 Baseline models bắt buộc

1. no-effect baseline;
2. global action attenuation;
3. global speed scalar;
4. non-connectome phenomenological age curve;
5. connectome-only model không neuromodulation;
6. disease-specific latent model.

Nếu model phức tạp không thắng baseline đơn giản trên held-out study thì chưa có bằng chứng rằng connectome hoặc cơ chế thêm vào tạo predictive value.

### 14.5 Ablation

Paper alpha-syn nên thử:

- bỏ connectome constraint;
- bỏ age state;
- bỏ assay model;
- all-DA thay selected population;
- bỏ VNC/CPG;
- global action attenuation comparator;
- deterministic best fit thay uncertainty ensemble.

Paper PINK1 nên thêm:

- bỏ serotonin state;
- bỏ SERT state;
- bỏ genotype-intervention interaction;
- gộp PPL1/PPL2;
- dopamine-neuron-loss-only model.

### 14.6 Sensitivity và identifiability

Phải trả lời:

- tham số nào được dữ liệu ràng buộc;
- tham số nào chủ yếu theo prior;
- nhiều parameter set có tạo cùng phenotype không;
- prediction nào ổn định qua posterior ensemble;
- endpoint nào có information gain cao nhất.

Không chỉ báo cáo best-fit parameter.

---

## 15. Roadmap theo gate

### Gate A: khóa metric và hiện trạng runtime

Deliverables:

- canonical metric dictionary;
- audit khác biệt giữa `walking_speed` và `mean_planar_speed_mm_s`;
- raw action export;
- duration/unit audit;
- versioned healthy baseline.

Exit criteria:

- mọi figure/table truy về raw artifact;
- không trộn metric khác định nghĩa;
- baseline tái lập trên clean environment.

### Gate B: literature dataset v2

Deliverables:

- atomic endpoint registry cho toàn bộ paper;
- digitization có uncertainty;
- duplicate và source-risk flags;
- study-level split manifest;
- locked calibration/holdout allocation.

Exit criteria:

- mọi target có statistic, spread và experimental unit;
- không data leakage;
- target quan trọng có reviewer thứ hai.

### Gate C: virtual assay adapters

Ưu tiên:

1. individual circular/open arena;
2. vial/startle tracking;
3. negative geotaxis/climbing;
4. rotating vertical/gait assay.

Exit criteria:

- output dùng cùng endpoint definition với paper;
- threshold, duration và aggregation có test;
- synthetic test cho mỗi assay.

### Gate D: motor architecture

Deliverables:

- descending -> VNC/CPG interface;
- raw action trace;
- locomotor mode và turning;
- controller ablations;
- longer stable rollout.

Exit criteria:

- perturbation circuit tạo response có thể truy vết;
- giảm phụ thuộc vào black-box mapping đến 42 joints;
- healthy gait ổn định trong protocol dài hơn.

### Gate E: dopamine neuromodulation

Deliverables:

- population-specific DA release;
- receptor/target-class abstraction;
- functional-deficiency và survival-loss states;
- Riemensperger 2011 unit tests;
- Liessem direction tests.

Exit criteria:

- tốt hơn global gain baseline trên held-out endpoints;
- uncertainty được báo cáo;
- không biến neurotransmitter annotation thành receptor map không có nguồn.

### Gate F: alpha-syn progression paper

Deliverables:

- age-state model;
- Pokrzywa longitudinal calibration;
- Riemensperger/Haywood/Aggarwal tests;
- leave-one-study-out;
- ablation, sensitivity và failure analysis;
- reproducible release.

Exit criteria:

- thắng simple baselines trên held-out data;
- mô tả được progression và uncertainty;
- claim được adjudicate độc lập.

### Gate G: PINK1-serotonin model comparison

Deliverables:

- 5-HT/SERT slow state;
- PPL1/PPL2 distinction;
- nonlinear genotype-dependent intervention;
- comparison H1-H5;
- danh sách thí nghiệm đề xuất cho external labs.

Exit criteria:

- serotonin model có predictive gain sau complexity penalty;
- kết quả ổn định qua uncertainty;
- nếu không phân biệt được, công bố non-identifiability.

### Gate H: lab-acceleration benchmark

Dù chưa có lab partner, có thể đánh giá retrospective:

- giả vờ che một tập condition đã biết;
- cho model chọn k condition;
- so với random, uncertainty sampling và simple heuristic;
- đo số condition cần để tìm phenotype/intervention rank đúng;
- đánh giá calibration của prediction intervals.

Trước khi external lab thực sự sử dụng, chỉ nên nói `designed to support experiment prioritization`, chưa nói `proven to accelerate laboratories`.

---

## 16. Điều kiện để paper có sức nặng

Một paper mạnh cần:

- câu hỏi sinh học rõ;
- data split nghiêm ngặt;
- simple baselines;
- held-out generalization;
- uncertainty;
- ablation;
- negative results;
- source provenance;
- reproducibility;
- claim đúng với evidence.

Với điều kiện không có wet-lab, nhóm phù hợp hơn với computational neuroscience, systems biology, bioinformatics hoặc methods venues. Một journal paper tốt vẫn khả thi nếu multi-study validation mạnh. Broad experimental-biology impact sẽ khó hơn nếu không có prospective biological data.

Để tăng sức nặng, cần chứng minh:

1. model phức tạp tốt hơn baseline đơn giản;
2. connectome/neuromodulation thực sự thêm predictive value;
3. model khái quát qua paper/lab/assay;
4. uncertainty được hiệu chỉnh;
5. model phát hiện được inconsistency hoặc robust prediction mà meta-analysis đơn giản không cung cấp.

---

## 17. Claim matrix cho toàn nhóm

| Tình huống | Được nói | Không được nói |
| --- | --- | --- |
| Healthy rollout PASS | Runtime tạo locomotion và artifact hợp lệ | Healthy fly đã biological validation |
| Disease proxy đổi speed | Perturbation computational ảnh hưởng output | Gene gây phenotype qua cơ chế đã mô phỏng |
| Cùng chiều paper | Directional concordance | Quantitative validation |
| Fit calibration data | Calibration fit | External prediction |
| Tốt trên held-out paper | External computational validation trong phạm vi study | Tương đương ruồi thật |
| Intervention proxy rescue | Mô hình dự đoán rescue endpoint | Thuốc có hiệu lực sinh học/lâm sàng |
| Model A thắng B | A có predictive adequacy tốt hơn trong candidate set | A là cơ chế thật duy nhất |
| Active design đề xuất experiment | Hỗ trợ ưu tiên thí nghiệm | Đã chứng minh tăng tốc lab |

Claim lock chính thức:

- [`docs/claims/current_claim_lock.md`](../../docs/claims/current_claim_lock.md)
- [`docs/release/final_project_claim.md`](../../docs/release/final_project_claim.md)

---

## 18. Rủi ro và kiểm soát

### 18.1 Overfitting

Kiểm soát bằng:

- study-level holdout;
- shared parameters;
- priors/regularization;
- simple baselines;
- posterior predictive checks.

### 18.2 Assay mismatch

Không chuyển tùy tiện:

- climbing -> speed;
- activity time -> walking speed;
- distance -> speed;
- median -> mean;
- group-vial unit -> individual-fly unit.

### 18.3 Driver/root-ID mismatch

Kiểm soát bằng:

- versioned mapping;
- probabilistic mapping nếu cần;
- mapping uncertainty;
- giữ nhãn class-level khi không có root IDs đáng tin cậy.

### 18.4 Source quality

- Poddighe: Expression of Concern.
- Pugliese: preprint flag.
- Cha OA: duplicate.
- Figure-only target: digitization uncertainty.

### 18.5 Simulator artifact bị hiểu nhầm là biology

Kiểm soát bằng:

- controller ablation;
- burden=0 identity test;
- inspect raw actions, joint trajectories và contacts;
- so neural-level với action-level perturbation;
- không gọi non-monotonic controller response là hormesis nếu không có bằng chứng.

### 18.6 Licensing và dependency

- Pin source commit và SHA256.
- Tuân FlyWire CC BY-NC và citation requirements.
- Không dùng đường dẫn cá nhân làm dependency tái lập.
- Có download/verification script cho checkpoint ngoài repo.

---

## 19. Phân công cho teammate

### Track 1: literature và data

- Chuẩn hóa metadata tất cả source.
- Đưa Riemensperger 2011 vào source registry hợp lệ.
- Digitize Pokrzywa time series.
- Chuẩn hóa PINK1-serotonin endpoints.
- Ghi đúng sample unit và spread type.
- Gắn duplicate/source-risk flags.

Output:

- `literature_endpoint_registry_v2.csv`;
- `study_split_manifest.yaml`;
- digitization audit.

### Track 2: assay và metrics

- Audit speed definitions qua các gate.
- Circular/open-arena adapter.
- Vial/startle adapter.
- Climbing metric.
- Bouts, pause, turning và gait.
- Raw-action export.

### Track 3: neural và neuromodulation

- Population-level dopamine state.
- Volume/receptor abstraction.
- Functional loss vs survival loss.
- Mapping uncertainty.
- alpha-syn age plugin.

### Track 4: VNC và body

- Review Pugliese scope.
- Descending -> VNC/CPG interface.
- Longer stable rollout.
- Motor-mode/turning outputs.
- Controller ablations.

### Track 5: statistics và evaluation

- Hierarchical observation model.
- Leave-one-study-out runner.
- Posterior-predictive metrics.
- Baseline comparison.
- Identifiability và sensitivity.

### Track 6: reproducibility và claims

- Manifest/checksum.
- Config/version locks.
- Data-leakage audit.
- Claim adjudication.
- Release package.

---

## 20. Việc cần làm ngay theo thứ tự

1. Khóa quyết định: paper đầu chỉ alpha-syn/dopamine, không multi-gene.
2. Audit `walking_speed` và `mean_planar_speed_mm_s` qua mọi gate.
3. Xây strategy cho duration dài hơn 0.5 giây hoặc segmented surrogate có kiểm định.
4. Hoàn thiện endpoint registry cho Riemensperger 2011/2013, Pokrzywa, Haywood, Aggarwal và Dimitrescu.
5. Khóa study-level split trước khi sửa model.
6. Xây circular/open-arena và vial/startle observation models.
7. Thêm dopamine neuromodulation; giữ global gain làm baseline.
8. Thêm alpha-syn age-state plugin.
9. Tích hợp VNC/CPG ở mức đủ cho causal tracing.
10. Chạy baselines, ablation và leave-one-study-out.
11. Công bố failure cases, đặc biệt Pozo mismatch và non-monotonic burden response.
12. Chỉ mở PINK1-serotonin flagship sau khi paper alpha-syn ổn định.

---

## 21. Decision record

### Đã quyết định

- Không có wet-lab nội bộ.
- Dùng dữ liệu ruồi thật đã công bố cho calibration và external computational validation.
- Không claim virtual fly tương đương live fly.
- alpha-syn/dopamine là hướng paper đầu tiên.
- PINK1-serotonin là flagship tiếp theo.
- LRRK2 intracellular transport là dự án riêng hoặc giai đoạn sau.
- Parkin/JNK và DJ-1/stress là future modules.
- Poddighe không phải primary quantitative source.
- Pugliese là preprint motor hypothesis, không phải disease truth.
- Hai file Cha là một source.
- Generic multi-gene scalar burden không phải kiến trúc mục tiêu.

### Chưa khóa

- Source nào là primary calibration trong fold đầu.
- Mức VNC fidelity tối thiểu cho paper alpha-syn.
- Raw data có đủ cho hierarchical likelihood hay cần digitized summaries.
- Dopamine-receptor abstraction và priors cụ thể.
- Tiêu chí thành công định lượng cho held-out prediction.
- Venue và manuscript scope cuối cùng.

Các quyết định chưa khóa phải được ghi trong analysis plan trước final run.

---

## 22. Chỉ mục repo

### Kiến trúc và khoa học

- [`docs/01_kien_truc.md`](../../docs/01_kien_truc.md)
- [`docs/02_mo_hinh_neural.md`](../../docs/02_mo_hinh_neural.md)
- [`docs/03_disease_profiles.md`](../../docs/03_disease_profiles.md)
- [`docs/literature_constrained_pipeline.md`](../../docs/literature_constrained_pipeline.md)
- [`docs/pre_disease_readiness_audit.md`](../../docs/pre_disease_readiness_audit.md)

### Literature và mapping

- [`research/paper_review/paper_summary.md`](paper_summary.md)
- [`research/paper_review/paper_analysis_vi.csv`](paper_analysis_vi.csv)
- [`research/paper_review/selected_sources.csv`](selected_sources.csv)
- [`research/disease_mapping/disease_condition_readiness.csv`](../disease_mapping/disease_condition_readiness.csv)
- [`docs/disease_rollouts/gene_specific_mapping_handoff_vi.md`](../../docs/disease_rollouts/gene_specific_mapping_handoff_vi.md)

### Kết quả và claim

- [`docs/healthy_baseline_methods_and_evidence.md`](../../docs/healthy_baseline_methods_and_evidence.md)
- [`docs/disease_rollouts/gate_12g_integrated_proxy_rollout_report.md`](../../docs/disease_rollouts/gate_12g_integrated_proxy_rollout_report.md)
- [`docs/disease_rollouts/gate_22_parkin_healthy_comparison_report.md`](../../docs/disease_rollouts/gate_22_parkin_healthy_comparison_report.md)
- [`docs/holdout/gate_23_pozo_holdout_validation_report.md`](../../docs/holdout/gate_23_pozo_holdout_validation_report.md)
- [`docs/claims/current_claim_lock.md`](../../docs/claims/current_claim_lock.md)
- [`docs/release/final_project_claim.md`](../../docs/release/final_project_claim.md)

---

## 23. Kết luận cuối cho toàn nhóm

Repo hiện không phải một biological Parkinson model hoàn chỉnh, nhưng đã có nền engineering và provenance đủ tốt để phát triển thành một nghiên cứu computational nghiêm túc. Điểm yếu lớn nhất nằm ở disease semantics, neuromodulation, assay compatibility và external validity, không phải ở việc thiếu thêm một tên gene trong config.

Bước chuyển quan trọng nhất là:

```text
Từ:
gene label -> burden -> action attenuation -> speed

Sang:
disease-specific latent state
    -> neuromodulation/cell state
    -> brain/VNC/body
    -> assay-specific observation
    -> study-level external validation
```

Nếu nhóm thực hiện được chuyển đổi này và đánh giá bằng leave-one-study-out, uncertainty, ablation và simple baselines, dự án có khả năng tạo paper computational neuroscience/systems biology có trọng lượng. Nếu tiếp tục thêm gene vào cùng một proxy và fit từng ratio riêng lẻ, số lượng artifact sẽ tăng nhưng sức nặng khoa học không tăng tương ứng.

Thông điệp chung cần giữ:

> Mục tiêu không phải thay thế ruồi thật. Mục tiêu là xây một hệ thống có thể tổng hợp bằng chứng, loại các giả thuyết không nhất quán, định lượng uncertainty và ưu tiên thí nghiệm có giá trị cao cho các phòng lab.
