# Pipeline cuối cùng để xây dựng và công bố bài báo

**Tên dự án:** Tái lập có kiểm soát các kiểu hình vận động Drosophila liên quan
Parkinson từ literature trên ruồi ảo FlyGym/MuJoCo
**Loại đóng góp:** paper-guided computational experiment và reproducible research
software
**Phạm vi hiện tại:** organism/action-level Parkinson-like locomotion proxy
**Trạng thái:** `PUBLICATION_PIPELINE_DEFINED`
**Ngày:** 2026-09-07

## 1. Luận đề của bài báo

Bài báo không tuyên bố đã tạo ra một mô hình Parkinson sinh học hoàn chỉnh. Luận
đề có thể kiểm chứng là:

> Một pipeline có provenance có thể chuyển các phenotype vận động được báo cáo trong
> paper về Drosophila thành virtual experiment có protocol, seed, metric, QC,
> calibration và holdout rõ ràng; từ đó đo được endpoint nào có thể tái lập, endpoint
> nào chỉ phù hợp để đối chiếu định tính và mismatch nào chỉ ra giới hạn của proxy
> hoặc capability của virtual assay.

Đây là câu hỏi về khả năng tái lập computational trong phạm vi được định nghĩa,
không phải tuyên bố về chẩn đoán, cơ chế bệnh, hiệu quả thuốc hoặc thay thế wet-lab.

## 2. Thiết kế tổng thể

```text
paper + supplementary + metadata
        |
        v
phenotype registry + provenance + human review
        |
        v
endpoint/assay bridge policy
        |
        +--> calibration target     +--> holdout target
        |                            |
        v                            v
preregistered proxy/config      independent holdout protocol
        |                            |
        +------------+---------------+
                     v
        FlyGym/MuJoCo virtual fly rollout
                     |
                     v
        QC -> seed-level metrics -> manifest/checksum/video
                     |
                     v
        baseline comparison -> direction/magnitude/mismatch
                     |
                     v
        claim adjudication -> manuscript/release package
```

Hai repository giữ ranh giới riêng:

- `drosophila-pd-flygym`: FlyGym/MuJoCo, body, controller, action lifecycle,
  physics, rollout, metrics, QC và viewer.
- `drosophila-pd-neural-disease`: paper review, phenotype/provenance, target policy,
  calibration/holdout, disease condition metadata và proxy adapter.

Extension chỉ tích hợp qua public perturbation contract; không copy hoặc sửa source
platform để làm cho kết quả khớp paper.

## 3. Các cổng bắt buộc

### Gate A - Khóa câu hỏi và phạm vi

Tạo một experiment registry có:

- câu hỏi nghiên cứu và giả thuyết;
- endpoint chính/phụ;
- condition, control và intervention/proxy;
- seed list, timestep, duration, world, controller và device;
- tiêu chí QC và tiêu chí loại rollout;
- phân bổ calibration/holdout;
- claim lock và scientific boundary.

**Đầu ra:** config versioned, manifest kế hoạch và protocol được review.

Không được đổi proxy hoặc metric sau khi xem holdout mà không tạo version experiment
mới.

### Gate B - Khóa evidence literature

Mỗi phenotype record phải truy được tới PDF, DOI/PMID, figure/table hoặc
supplementary. Reviewer phải kiểm tra:

- genotype/model và control;
- tuổi, giới tính, cohort và sample unit;
- arena, stimulus, duration và điều kiện assay;
- metric, đơn vị, statistic trung tâm và uncertainty nguyên gốc;
- treatment/intervention và giới hạn của paper.

Các trạng thái được phép:

- `CALIBRATION_ELIGIBLE`;
- `HOLDOUT_ELIGIBLE`;
- `VALIDATION_ONLY`;
- `NOT_COMPARABLE`;
- `WAITING_TARGET_DATA`.

Không đổi median thành mean, không đổi SE/SEM/SD/IQR/range/CI95 cho nhau và không
đoán số từ hình nếu chưa có policy digitization được duyệt.

### Gate C - Khóa assay bridge

Chỉ chuyển một endpoint thành target số khi virtual endpoint có cùng khái niệm,
đơn vị và statistic, hoặc có conversion vật lý minh bạch.

| Paper endpoint | Xử lý trong pipeline |
| --- | --- |
| Adult horizontal walking speed/velocity | Có thể calibration nếu target và transfer được duyệt |
| Distance/path length | Holdout distance riêng; không đổi thành speed |
| Climbing/negative geotaxis | Validation-only cho tới khi có virtual assay riêng |
| DAM activity | Validation-only hoặc not comparable với walking speed |
| Flight/tremor/PER | Chờ capability và metric riêng |

**Đầu ra:** assay transfer decision, unit-of-analysis, uncertainty policy và reviewer
provenance.

### Gate D - Runtime và artifact preflight

Kiểm tra platform contract, brain source/checkpoint, license, checksum, mapping,
environment và GPU trước khi chạy:

```powershell
python scripts/check_platform_contract.py `
  --platform-root ..\drosophila-pd-flygym --json
python scripts/audit_calibration_targets.py
python -m compileall -q src scripts tests
python -m pytest -q -rs -p no:cacheprovider
```

Nếu brain source hoặc checkpoint không có provenance hợp lệ, trạng thái phải là
`WAITING_PLATFORM_NEURAL_RUNTIME`. Không tạo rollout giả để vượt gate.

### Gate E - Healthy baseline

Chạy healthy trước disease với cùng physics, timestep, controller, duration,
renderer và seed policy sẽ dùng cho disease. Tối thiểu nên có nhiều seed độc lập,
ví dụ `0..4` hoặc `0..5` theo config đã khóa.

Mỗi seed phải kiểm tra:

- đủ frame và timestamp tăng đều;
- không NaN/Inf;
- thorax/contact hợp lệ;
- locomotion có displacement/path length;
- joint và action trajectory có thay đổi;
- orientation hợp lệ;
- metric contract đầy đủ;
- manifest/checksum khớp.

Baseline phải đạt `HEALTHY_BASELINE_RUNTIME_PASS` trước khi diễn giải disease.
Raw artifact lớn có thể hash rồi xóa sau QC bằng `--discard-raw`; metrics, logs,
manifest và report phải được giữ.

### Gate F - Exploratory disease proxy

Dùng một grid burden được khai báo trước, giữ nguyên physics và seed policy. Mỗi
condition phải ghi:

- tên condition và scope organism/action-level;
- proxy operator và tham số;
- target neuron/edge nếu có, hoặc ghi rõ chưa có gene-specific mapping;
- input/checkpoint provenance;
- số seed, output và QC.

Trong phạm vi hiện tại, nhãn `alpha_synuclein`, `pink1`, `parkin`, `dj1` hoặc
`lrrk2` không tự chứng minh gene-specific disease model. Nếu chưa có root-ID/edge
mapping độc lập, phải dùng wording `organism-level computational proxy`.

### Gate G - Chen-only calibration

Chỉ dùng target Chen đã approved cho calibration. Calibration được chọn trong grid
đã khóa, không dùng Pozo và không thay đổi target sau khi xem kết quả.

Báo cáo phải ghi:

- target paper/figure và unit;
- statistic và uncertainty đúng nguyên gốc;
- objective và loss/selection rule;
- toàn bộ candidate burden;
- burden được chọn và lý do;
- seed dùng trong calibration;
- seed độc lập cho confirmation.

Kết quả chỉ được gọi là `computational calibration`, không phải biological
validation.

### Gate H - Confirmation độc lập

Chạy lại burden đã khóa với seed độc lập, cùng protocol và không sửa tham số. Báo
cáo sự ổn định của ratio, mean, SD/SE hoặc CI tính từ seed-level data. Nếu rerun
không tái hiện kết quả, giữ trạng thái `NOT_REPRODUCED` hoặc ghi mismatch.

### Gate I - Pozo holdout

Pozo phải được giữ ngoài calibration. Nếu dùng `distance_traveled_mm`, chỉ so sánh
distance/path-length với virtual distance.

Report phải tách:

1. directionality: cùng chiều hay ngược chiều;
2. magnitude/ratio: gần hay lệch;
3. uncertainty và sample unit;
4. assay confound và capability gap.

Directional concordance với quantitative mismatch không được gọi là quantitative
validation.

### Gate J - Robustness và negative controls

Trước khi viết kết luận, chạy các kiểm tra:

- nhiều seed ngoài seed calibration;
- burden bằng 0 và burden dương;
- perturbation invariance hoặc control operator nếu phù hợp;
- sensitivity với timestep/controller parameter trong phạm vi đã đăng ký;
- kiểm tra action không mutate ngoài ý muốn;
- lặp lại artifact từ manifest/checksum.

Không chọn phiên bản tốt nhất bằng holdout. Mọi thay đổi sau kết quả phải tạo
config/version mới và được ghi trong decision log.

## 4. Bộ số liệu và phân tích cuối

### Endpoint chính

- `mean_planar_speed_mm_s`;
- `distance_traveled_mm`;
- net planar displacement;
- trajectory efficiency nếu assay bridge được duyệt.

### Endpoint phụ

- heading variance;
- joint velocity và symmetry;
- orientation stability;
- contact ratio;
- timestamp/timestep consistency.

Đơn vị phân tích là seed/run, không phải frame. Report cần có bảng từng seed, mean,
sample SD, SE hoặc bootstrap CI phù hợp. Không dùng seed-level SD để thay uncertainty
của cohort ruồi thật.

### Hình và bảng tối thiểu cho manuscript

1. Sơ đồ pipeline paper-to-virtual-fly.
2. Bảng provenance và assay transfer.
3. QC Healthy baseline theo seed.
4. Dose-response/proxy response với confidence interval.
5. Chen calibration objective và confirmation độc lập.
6. Pozo holdout: direction, ratio và mismatch.
7. Bảng capability gap: endpoint nào tái lập được, validation-only hoặc blocked.
8. Một video representative có config/seed/provenance.

## 5. Tiêu chí quyết định kết quả

Mỗi experiment cuối phải nhận đúng một trạng thái:

- `REPRODUCED_COMPUTATIONALLY_WITHIN_DEFINED_SCOPE`;
- `DIRECTIONALLY_CONCORDANT_QUANTITATIVE_MISMATCH`;
- `VALIDATION_ONLY`;
- `NOT_COMPARABLE`;
- `NOT_REPRODUCED`;
- `WAITING_TARGET_DATA`;
- `WAITING_PLATFORM_CAPABILITY`.

Không có trạng thái nào tự mang nghĩa biological Parkinson validation.

## 6. Cấu trúc artifact công bố

```text
release/
  manuscript_vi.md
  manuscript_en.md
  figures/
  tables/
  configs/
  manifests/
  checksums.sha256
  reports/
  videos/
  environment/
  README_reproduce.md
```

Raw rollout lớn không nhất thiết đưa lên GitHub. Có thể lưu ở release storage,
Zenodo hoặc kho dữ liệu phù hợp với license; repository giữ checksum, manifest,
metrics nhẹ và lệnh tái lập.

Mọi artifact phải phân biệt:

- `verified current`;
- `historical`;
- `planned`;
- `waiting/blocked`.

## 7. Cấu trúc bài báo đề xuất

### Introduction

Nêu khoảng trống: paper về ruồi thật có nhiều phenotype nhưng khó chuyển đồng nhất
sang virtual assay. Đặt mục tiêu là kiểm tra khả năng tái lập có kiểm soát, không
khẳng định mô phỏng đầy đủ bệnh.

### Methods

Mô tả paper registry, review, assay bridge, FlyGym/MuJoCo, controller/action
contract, proxy, seed policy, QC, calibration, confirmation, holdout và checksum.

### Results

Trình bày healthy runtime, disease proxy response, Chen calibration, independent
confirmation, Pozo holdout và mismatch/capability gap. Tách kết quả hiện tại khỏi
historical artifact.

### Discussion

Giải thích ý nghĩa của directional concordance, quantitative mismatch, assay
confound và giới hạn mapping. Nêu rõ mô hình chưa chứng minh neuron loss, dopamine
biology, protein aggregation hay gene-specific mechanism.

### Reproducibility and limitations

Đưa version, commit, environment, config, seed, manifest, checksum, storage policy,
license và toàn bộ blocker chưa giải quyết.

## 8. Claim lock cho bản gửi

### Wording được phép

> Chúng tôi xây dựng một paper-guided virtual experiment pipeline để đánh giá các
> kiểu hình vận động Drosophila liên quan Parkinson trong các assay có thể chuyển
> đổi sang FlyGym/MuJoCo. Pipeline tách calibration khỏi holdout, lưu provenance ở
> cấp seed và báo cáo cả concordance lẫn mismatch.

### Wording không được phép

- biological Parkinson validation;
- gene-specific validated model;
- chứng minh neuron loss, dopamine depletion hoặc alpha-synuclein aggregation;
- clinical prediction, diagnosis hoặc drug efficacy;
- thay thế thí nghiệm trên ruồi thật;
- paper fully replicated khi chỉ khớp một endpoint.

## 9. Điều kiện sẵn sàng gửi bài

Chỉ gửi manuscript khi tất cả mục sau đã được đánh dấu:

- [ ] Câu hỏi, hypothesis và claim lock đã khóa.
- [ ] Literature record có provenance figure/PDF và reviewer.
- [ ] Target calibration và holdout được tách độc lập.
- [ ] Healthy baseline đạt runtime/QC bằng protocol hiện tại.
- [ ] Disease positive-burden rollout có đủ seed, metrics và manifest.
- [ ] Chen calibration và confirmation đã re-run trên contract hiện tại.
- [ ] Pozo holdout được chạy độc lập và mismatch được báo cáo.
- [ ] Không có NaN/Inf, missing artifact hoặc checksum mismatch.
- [ ] Figures/tables truy ngược được về metrics seed-level.
- [ ] Supplementary có config, environment và lệnh tái lập.
- [ ] License của brain/checkpoint/dataset đã được kiểm tra.
- [ ] Co-author và reviewer thứ hai đã duyệt số liệu, wording và giới hạn.

Nếu còn một mục chưa đạt, manuscript phải ghi trạng thái `NOT_READY_FOR_SUBMISSION`
hoặc giới hạn claim tương ứng.

## 10. Kết luận

Pipeline này khả thi để tạo một bài về computational biology/scientific software và
virtual experiment. Giá trị chính là biến paper về ruồi thật thành quy trình virtual
có thể kiểm tra, so sánh và tái lập; không phải ép virtual fly thành bản sao sinh
học hoàn chỉnh.

Kết quả mạnh nhất của bài không nhất thiết là mọi metric đều khớp. Một kết quả có
giá trị là: endpoint nào tái lập được trong phạm vi định nghĩa, endpoint nào chỉ
đúng chiều, mismatch ở đâu, và capability nào cần phát triển tiếp để kiểm tra giả
thuyết tốt hơn.
