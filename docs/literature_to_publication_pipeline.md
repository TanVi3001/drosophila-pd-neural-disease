# Pipeline từ literature đến publication

## Phạm vi khoa học

Dự án xây dựng một **computational Drosophila Parkinson-like locomotion model**: một mô hình vận động tính toán có ràng buộc từ connectome/runtime và evidence phenotype. Mô hình không thay thế mô hình Parkinson sinh học, không phải mô hình chẩn đoán, không dự đoán lâm sàng, không phải công cụ thử thuốc và không chứng minh cơ chế tế bào ở người.

## Câu hỏi trung tâm

Các perturbation neural/action-level được ràng buộc bởi literature có làm thay đổi các chỉ số locomotion của Drosophila trong FlyGym theo hướng và cấu trúc có thể kiểm tra lại trên dữ liệu công bố hay không?

Kết quả phải được diễn giải theo ba lớp: (1) simulation vận động, (2) concordance với endpoint của paper, (3) giới hạn của phép chuyển assay. Không dùng một kết quả số để kết luận bệnh sinh học.

## Sơ đồ pipeline

```text
Paper/PDF chính thức
        |
        v
Human screening và source provenance
        |
        v
Phenotype record + statistic + uncertainty + unit of analysis
        |
        v
Metric mapping và disease-layer proxy mapping
        |
        v
Connectome/checkpoint/license audit
        |
        v
Healthy baseline nhiều seed
        |
        v
Gene/condition disease rollout nhiều seed
        |
        +--> sensitivity/ablation/response curves
        |
        v
Calibration targets đã approved  --------> Holdout targets độc lập
        |                                      |
        v                                      v
Calibration loss và fitted parameters      Blind/locked validation
        \                                      /
         v                                    v
Computational concordance + uncertainty + limitations
        |
        v
Figures, tables, supplementary, manuscript
        |
        v
Reproducible release: code, manifest, checksum, DOI
```

## Giai đoạn 0: khóa provenance

1. Giữ paper registry, source URL, PMID/DOI, file name, hash và license status.
2. PDF trong `temporary/` không được mặc định đưa lên GitHub; khi phát hành chỉ đưa metadata/link nếu quyền phân phối không rõ.
3. Khóa version Python, FlyGym, MuJoCo, source connectome/checkpoint, config, seed policy và renderer.
4. Không gọi `selected_sources.csv` là dataset phenotype đã được phê duyệt; đây là source inventory.

## Giai đoạn 1: human literature curation

Reviewer đọc Methods, Results, hình, bảng và supplementary. Mỗi record ghi genotype, tuổi, giới tính, assay, metric, unit, sample size, statistic, uncertainty, figure/table/page và notes. Nếu không thấy, ghi `NOT_REPORTED` hoặc để trống theo schema; không đoán.

Chỉ primary data mới có thể làm evidence phenotype. Review, paper gait người và tài liệu IEEE ngoài lĩnh vực không đưa vào disease calibration corpus. Paper phương pháp như NeuroMechFly, CPG hoặc walking direction chỉ hỗ trợ cách hiểu controller/metric.

## Giai đoạn 2: mapping có kiểm soát

Mapping phải đi theo chuỗi:

`paper phenotype -> literature metric -> FlyGym metric -> disease proxy -> calibration/validation candidate`.

Một phenotype không chuyển được endpoint hoặc đơn vị thì giữ `VALIDATION_ONLY`/`NOT_COMPARABLE`. Ví dụ climbing, flight, survival và DAM beam-break không tự động thành `mean_planar_speed_mm_s`. Median không được đưa vào cột mean; distance không được gọi là speed.

Root-ID mapping là một nhiệm vụ riêng. Gene name không đủ để suy ra neuron subset. Mapping gene-specific chỉ hợp lệ khi có FlyWire/connectome version, root ID, cell type, driver/expression scope và nguồn xác nhận.

## Giai đoạn 3: baseline và experiment

Healthy phải chạy trước bằng cùng physics, morphology, controller, renderer, timestep, duration và seed protocol với disease condition. Tối thiểu dùng nhiều seed đã định trước; báo cáo cả mean, spread và số rollout hợp lệ.

Disease condition chỉ thay đổi các proxy có implementation và mapping hợp lệ. Với PINK1, Parkin, DJ-1, LRRK2 và alpha-synuclein, phải tách rõ:

- gene/genotype/driver trong paper;
- proxy computational đang dùng;
- neuron/edge scope đã được chứng minh;
- phần nào là hypothesis computational, phần nào là literature observation.

Mọi rollout phải lưu config, seed, input hash, output hash, metrics, manifest và nếu có video thì lưu quy tắc sinh video. Video là minh họa trajectory, không phải bằng chứng biological validation.

## Giai đoạn 4: calibration và holdout

Calibration chỉ dùng target có `review_status=approved`, đủ uncertainty/sample size/provenance và assay transfer được policy cho phép. Holdout phải được khóa trước khi fit, khác paper/cohort/record với calibration trong phạm vi có thể.

Không fit vào climbing/DAM nếu endpoint tương ứng chưa có trong simulation. Loss có thể báo RMSE, MAE, cosine hoặc Huber theo kế hoạch đã khóa; không chọn metric/loss sau khi thấy kết quả có lợi.

Sau calibration, chạy lại cùng protocol trên holdout. Báo cả kết quả calibration và holdout, số record bị loại, lý do loại, khoảng không chắc chắn và sensitivity với seed.

## Giai đoạn 5: concordance và thống kê

Concordance chỉ trả lời mô phỏng có phù hợp với endpoint literature ở mức computational hay không: `Strong`, `Moderate`, `Weak`, `Unknown` hoặc `Insufficient`. Không tính biological similarity và không gọi đó là tái tạo Parkinson.

Khi đủ replicate, sử dụng statistical analysis plan đã đăng trong repo: effect size, confidence interval, bootstrap/permutation hoặc mixed effects chỉ khi điều kiện áp dụng được thỏa mãn. Báo cáo unit of analysis, multiple-comparison strategy, missing data và exclusion criteria.

## Giai đoạn 6: publication package

### Câu chuyện bài báo đề xuất

1. Nền tảng embodied Drosophila và provenance của controller/connectome.
2. Disease Layer như tập perturbation computational có thể cấu hình.
3. Literature mapping có human review và policy chống overclaim.
4. Healthy baseline và disease-condition response surfaces nhiều seed.
5. Calibration trên target tương thích và validation trên holdout độc lập.
6. Những metric/assay không thể chuyển đổi và giới hạn của mô hình.

### Bộ kết quả tối thiểu

- Bảng source/phenotype với DOI/PMID và provenance.
- Bảng proxy, parameter, range và evidence status.
- Healthy vs condition với seed-level data.
- Calibration/holdout loss và uncertainty.
- Concordance matrix metric-proxy-paper.
- Ablation một proxy và combination perturbation chỉ khi có lý do khoa học.
- Figure trajectory/video đại diện, không chọn frame có lợi một cách hậu nghiệm.
- Manifest/checksum, environment specification, code/config và README tái lập.

### Ranh giới diễn giải

Có thể viết: “simulation cho thấy perturbation computational X liên quan đến thay đổi metric Y trong runtime FlyGym và có/không có concordance với endpoint literature tương thích”.

Không được viết nếu chưa có bằng chứng bổ sung: “mô hình mô phỏng neuron dopamine bị chết”, “đã tái tạo Parkinson”, “dự đoán bệnh nhân”, “thử được thuốc” hoặc “thay thế thí nghiệm ruồi thật”.

## Các cổng quyết định

| Gate | Điều kiện qua cổng | Nếu chưa đạt |
|---|---|---|
| G1 Source | PDF/DOI/PMID, hash và license status rõ | Giữ source ở review, không trích target. |
| G2 Curation | genotype, assay, metric, unit, sample size, statistic, uncertainty, figure/table | `PENDING_HUMAN_SIGNOFF`. |
| G3 Mapping | metric literature tương thích metric simulation và proxy có rationale | `VALIDATION_ONLY`/`NOT_COMPARABLE`. |
| G4 Runtime | healthy rollout hợp lệ, không NaN/Inf, trajectory/contact/timestamp hợp lệ | `WAITING_RUNTIME` hoặc `WAITING_HEALTHY_BASELINE`. |
| G5 Calibration | target approved, calibration/holdout tách, protocol khóa | `WAITING_TARGET_DATA`. |
| G6 Validation | holdout chạy độc lập và artifact đủ provenance | Không claim concordance mạnh. |
| G7 Release | figures/tables/code/data manifest tái lập, license hợp lệ | Chưa phát hành artifact/paper. |

## Trạng thái hiện tại và việc tiếp theo

Repo đã có platform, disease perturbation scaffold, target policy, audit, calibration/holdout evaluation, literature review records và source corpus mở rộng. Việc tiếp theo vẫn là human adjudication theo `docs/task_tuan_source_adjudication.md`, sau đó audit target. Chỉ khi audit thực sự trả `READY_FOR_CALIBRATION` mới được chạy calibration; tiếp theo mới là multi-seed gene-specific, holdout và concordance.
