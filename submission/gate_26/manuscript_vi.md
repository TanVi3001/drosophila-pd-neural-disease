# Manuscript Draft: Computational Drosophila Parkinson-like Locomotion Proxy

## Tieu de tieng Viet

**Pipeline virtual experiment co provenance cho phenotype van dong Parkinson-like
tren Drosophila: calibration Chen, holdout Pozo va bao cao mismatch dinh luong**

## Abstract (English)

We present a provenance-tracked virtual-experiment pipeline for Drosophila
Parkinson-like locomotor phenotypes in FlyGym/MuJoCo. A predeclared
organism-level proxy was calibrated with the Chen 2014 adult walking-speed
disease/control ratio and confirmed with a locked-parameter rerun. An
independent Pozo 2022 PINK1 distance holdout showed directional concordance,
whereas its simulated disease/control ratio remained quantitatively mismatched.
The contribution is a reproducible computational locomotion proxy workflow with
explicit assay boundaries, seed-level quality control, calibration/holdout
separation, manifests and checksums. It is not a biological, gene-specific,
clinical, or therapeutic validation of Parkinson disease.

## Tom tat

Nghien cuu xay dung pipeline virtual experiment truy vet duoc provenance de
chuyen cac endpoint van dong tu literature ve ruoi giấm sang artifact
computational trong FlyGym/MuJoCo. Healthy baseline, action contract, QC,
calibration Chen va holdout Pozo duoc tach thanh cac gate co manifest va
checksum. Ket qua cho phep ket luan ve computational locomotion proxy trong
pham vi ro rang, dong thoi giu lai mismatch dinh luong thay vi dieu chinh tham
so theo holdout.

## Cau hoi nghien cuu

Mot pipeline co provenance co the tai hien mot huong thay doi locomotion da
bao cao tren Drosophila trong virtual assay, trong khi tach calibration khoi
holdout va bao cao trung thuc cac mismatch hay khong?

## Phuong phap

1. Literature target duoc review theo genotype, assay, statistic, uncertainty,
   sample unit va assay-transfer policy.
2. Healthy FlyGym/MuJoCo baseline duoc chay nhieu seed cung physics, controller,
   timestep va QC trajectory/action/contact.
3. Proxy burden tac dong tren action contract cua runtime; scope duoc ghi ro la
   organism/class-level exploratory khi khong co mapping neuron/edge
   gene-specific da duyet.
4. Chen 2014 duoc dung duy nhat cho calibration ratio; parameter duoc khoa va
   xac nhan bang rerun doc lap.
5. Pozo 2022 duoc giu lam holdout distance; distance khong duoc doi thanh speed
   va holdout khong duoc dung de tune lai parameter.

## Ket qua

- Chen confirmation: observed ratio `0.6142225784195846`, target
  `0.6701030927835051`, status `PASS`.
- Pozo directionality giu `PASS`, nhung quantitative ratio co observed
  `0.9470070897697126`, target `0.19203837612811836`, status `MISMATCH`.
- Gate 21/22 cho runtime/comparison evidence o scope class-level exploratory;
  khong co gene-specific mapping validation.

## Dien giai

Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout concordance and substantial quantitative ratio mismatch.

Ket qua Pozo chi dong thuan ve huong; mismatch dinh luong la ket qua chinh
thuc cua bai bao. Seed la don vi runtime computational, khong duoc dien giai
nhu cohort sinh hoc doc lap va khong dung de tao claim p-value sinh hoc.

## Gioi han

- Khong co biological Parkinson validation.
- Khong co gene-specific validation cho PINK1, Parkin, DJ-1, LRRK2 hay
  alpha-synuclein.
- Virtual assay va paper assay co khac biet ve scale, duration va readout.
- Bai bao khong la cong cu chan doan, thuoc hay thay the wet-lab.

## Tinh tai lap

Package kem theo co config, metric table, five provenance-tracked figures,
manifest SHA256 va huong dan verify khong can GPU. Gate 25 la reproducibility
freeze cua evidence dung trong manuscript nay.
