# Gate 21: Parkin class-level exploratory rollout

Trang thai: `PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_PASS`

- Planned rollouts: `25`.
- Executed rollouts: `25`.
- Passed QC: `25`.
- Mapping: `DAN/dopaminergic class-level`, gene-specific: `False`.
- Calibration: `False`; holdout: `False`.

## Dien giai

Gate nay chi kiem tra computational neural perturbation pipeline tren mot mapping class-level da review. Cac he so burden la proxy sensitivity values duoc khai bao trong config; chung khong phai so do Parkin, dopamine hay ket qua calibration.

## QC per rollout

| Burden | Seed | Status | Speed | Distance | Displacement | Contact | Joint | Video |
| ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 0.0 | 0 | `PASS` | 1.5908596841868465 | 1.407676499241302 | 0.7954298420934233 | `PASS` | `PASS` | `PASS` |
| 0.0 | 1 | `PASS` | 1.7609458781828746 | 1.3758130625006904 | 0.8804729390914373 | `PASS` | `PASS` | `-` |
| 0.0 | 2 | `PASS` | 1.6287430491425956 | 1.6524886881762586 | 0.8143715245712978 | `PASS` | `PASS` | `-` |
| 0.0 | 3 | `PASS` | 1.8363745406613907 | 1.6540584548376787 | 0.9181872703306954 | `PASS` | `PASS` | `-` |
| 0.0 | 4 | `PASS` | 1.6828314800537074 | 1.5402164022849538 | 0.8414157400268537 | `PASS` | `PASS` | `-` |
| 0.25 | 0 | `PASS` | 1.5926758254175482 | 1.4094014993605946 | 0.7963379127087741 | `PASS` | `PASS` | `-` |
| 0.25 | 1 | `PASS` | 1.7609458781828746 | 1.3758130625006904 | 0.8804729390914373 | `PASS` | `PASS` | `-` |
| 0.25 | 2 | `PASS` | 1.6706309613235482 | 1.6807250958930524 | 0.8353154806617741 | `PASS` | `PASS` | `-` |
| 0.25 | 3 | `PASS` | 1.8362932875440061 | 1.6540326425419813 | 0.9181466437720031 | `PASS` | `PASS` | `-` |
| 0.25 | 4 | `PASS` | 1.6828314800537074 | 1.5402164022849538 | 0.8414157400268537 | `PASS` | `PASS` | `-` |
| 0.5 | 0 | `PASS` | 1.5938254167650714 | 1.4095995389779223 | 0.7969127083825357 | `PASS` | `PASS` | `-` |
| 0.5 | 1 | `PASS` | 1.7576115709499405 | 1.374636449646613 | 0.8788057854749702 | `PASS` | `PASS` | `-` |
| 0.5 | 2 | `PASS` | 1.627483080323328 | 1.6569897575108374 | 0.813741540161664 | `PASS` | `PASS` | `-` |
| 0.5 | 3 | `PASS` | 1.8179233846747824 | 1.6442060192469512 | 0.9089616923373912 | `PASS` | `PASS` | `-` |
| 0.5 | 4 | `PASS` | 1.6828649092794323 | 1.5402416535089394 | 0.8414324546397162 | `PASS` | `PASS` | `-` |
| 0.75 | 0 | `PASS` | 1.6254090900504192 | 1.4283312478921255 | 0.8127045450252096 | `PASS` | `PASS` | `-` |
| 0.75 | 1 | `PASS` | 1.757612066784017 | 1.374638260211662 | 0.8788060333920085 | `PASS` | `PASS` | `-` |
| 0.75 | 2 | `PASS` | 1.6271294998642913 | 1.6553454070736744 | 0.8135647499321457 | `PASS` | `PASS` | `-` |
| 0.75 | 3 | `PASS` | 1.8179233846747824 | 1.6442060192469512 | 0.9089616923373912 | `PASS` | `PASS` | `-` |
| 0.75 | 4 | `PASS` | 1.6828649092794323 | 1.5402416535089394 | 0.8414324546397162 | `PASS` | `PASS` | `-` |
| 1.0 | 0 | `PASS` | 1.5937247099829024 | 1.4095897756674518 | 0.7968623549914512 | `PASS` | `PASS` | `PASS` |
| 1.0 | 1 | `PASS` | 1.757612066784017 | 1.374638260211662 | 0.8788060333920085 | `PASS` | `PASS` | `-` |
| 1.0 | 2 | `PASS` | 1.6271294998642913 | 1.6553454070736744 | 0.8135647499321457 | `PASS` | `PASS` | `-` |
| 1.0 | 3 | `PASS` | 1.8179233846747824 | 1.6442060192469512 | 0.9089616923373912 | `PASS` | `PASS` | `-` |
| 1.0 | 4 | `PASS` | 1.6828649092794323 | 1.5402416535089394 | 0.8414324546397162 | `PASS` | `PASS` | `-` |

## Ranh gioi khoa hoc

Khong co gene-specific validation, biological Parkinson validation, calibration, holdout validation, clinical prediction hay drug validation trong Gate 21.

Metrics chi la output cua computational rollout va chi duoc tong hop khi rollout dat QC. Khong co metric nao duoc tao khi simulation bi block.
