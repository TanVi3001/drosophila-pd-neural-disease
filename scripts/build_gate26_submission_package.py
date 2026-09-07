"""Build the compact, claim-safe Gate 26 manuscript submission package.

This script only reads checksum-tracked Gate 24/25 artifacts and writes a
manuscript package. It never starts CUDA, FlyGym, calibration, holdout
validation, tuning, or a new simulation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_26_submission_package/configs/submission_package.yaml"
DEFAULT_PACKAGE = ROOT / "submission/gate_26"
DEFAULT_EXPERIMENT = ROOT / "experiments/gate_26_submission_package"
DEFAULT_REPORT = ROOT / "docs/submission/gate_26_submission_package_report.md"


class SubmissionPackageError(ValueError):
    """Raised when a Gate 26 source artifact is absent or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise SubmissionPackageError(f"Path is outside the repository: {path}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionPackageError(f"Invalid JSON: {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise SubmissionPackageError(f"Expected a JSON object: {_relative(path)}")
    return value


def _read_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise SubmissionPackageError("Gate 26 config must be a YAML mapping")
    return value


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_checksum_file(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            digest, relative = line.split("  ", maxsplit=1)
        except ValueError as exc:
            raise SubmissionPackageError(f"Invalid checksum line in {_relative(path)}") from exc
        checksums[relative] = digest
    if not checksums:
        raise SubmissionPackageError(f"Empty checksum file: {_relative(path)}")
    return checksums


def _verify_gate25_freeze() -> dict[str, str]:
    path = ROOT / "experiments/gate_25_reproducibility_freeze/manifests/checksums.sha256"
    checksums = _read_checksum_file(path)
    for relative, expected in checksums.items():
        artifact = ROOT / relative
        if not artifact.is_file() or _sha256(artifact) != expected:
            raise SubmissionPackageError(f"Gate 25 checksum mismatch: {relative}")
    return checksums


def _validate_sources(config: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    prohibited = ("run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning")
    if config.get("analysis_only") is not True or any(config.get(key) is not False for key in prohibited):
        raise SubmissionPackageError("Gate 26 must stay analysis-only")

    manifests: dict[str, dict[str, Any]] = {}
    for item in config["required_manifests"]:
        path = ROOT / item["path"]
        document = _read_json(path)
        if document.get("status") != item["expected_status"]:
            raise SubmissionPackageError(
                f"Unexpected {item['name']} status: {document.get('status')!r}"
            )
        manifests[str(item["name"])] = document

    gate24 = manifests["gate_24_concordance"]
    if gate24.get("pozo_quantitative_match") is not False:
        raise SubmissionPackageError("Pozo quantitative mismatch must remain explicit")
    if gate24.get("gene_specific_validation") is not False:
        raise SubmissionPackageError("Gene-specific validation must remain unavailable")
    if gate24.get("biological_parkinson_validation") is not False:
        raise SubmissionPackageError("Biological validation must remain unavailable")
    gate25 = manifests["gate_25_reproducibility_freeze"]
    if any(gate25.get(key) is not True for key in ("no_gpu", "no_simulation", "no_calibration", "no_holdout_validation", "no_tuning")):
        raise SubmissionPackageError("Gate 25 no-execution guarantees are incomplete")
    return manifests, _verify_gate25_freeze()


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SubmissionPackageError(f"Empty table: {_relative(path)}")
    return rows


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _write_evidence_table(path: Path) -> None:
    rows = [
        {
            "evidence": "Chen 2014 calibration",
            "gate": "13B/13C",
            "endpoint": "mean_planar_speed_ratio",
            "result": "Computational calibration and locked-parameter confirmation",
            "claim_scope": "organism-level computational proxy",
        },
        {
            "evidence": "Parkin exploratory rollout",
            "gate": "21/22",
            "endpoint": "multi-seed locomotion metrics",
            "result": "Runtime and comparison evidence",
            "claim_scope": "class-level exploratory only",
        },
        {
            "evidence": "Pozo 2022 holdout",
            "gate": "23/24",
            "endpoint": "distance_traveled_mm ratio",
            "result": "Directional PASS; quantitative MISMATCH",
            "claim_scope": "organism-level proxy holdout",
        },
        {
            "evidence": "Gene-specific biology",
            "gate": "24",
            "endpoint": "reviewed neuron/edge mapping",
            "result": "NOT_AVAILABLE",
            "claim_scope": "no gene-specific validation",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _manuscript(config: Mapping[str, Any], concordance: list[dict[str, str]]) -> str:
    status = {row["evidence_id"]: row for row in concordance}
    chen = status["chen_confirmation"]
    pozo = status["pozo_quantitative_ratio"]
    return f"""# Manuscript Draft: Computational Drosophila Parkinson-like Locomotion Proxy

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

- Chen confirmation: observed ratio `{chen['observed']}`, target
  `{chen['target']}`, status `{chen['status']}`.
- Pozo directionality giu `PASS`, nhung quantitative ratio co observed
  `{pozo['observed']}`, target `{pozo['target']}`, status `{pozo['status']}`.
- Gate 21/22 cho runtime/comparison evidence o scope class-level exploratory;
  khong co gene-specific mapping validation.

## Dien giai

{config['claim_lock']['allowed']}

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
"""


def _readme(config: Mapping[str, Any]) -> str:
    return f"""# Gate 26 Submission Package

**Status:** `{config['package_status']}`

Package nay dong goi manuscript draft, figures, tables va checksum cua evidence
da khoa den Gate 25. No phu hop cho internal review hoac mot computational-proxy
manuscript/preprint workflow; khong phai bang chung Parkinson sinh hoc,
gene-specific, lam sang hay dieu tri.

## Kiem tra doc lap

```powershell
py -3.12 scripts/verify_gate26_submission_package.py
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Khong can GPU de kiem tra package. Chi cai `.[analysis]` neu can tao lai PNG
cua Gate 24 tu dau.
"""


def _report(config: Mapping[str, Any], count: int) -> str:
    return f"""# Gate 26: Manuscript, figures, tables va independent verification

**Trang thai:** `{config['package_status']}`

Gate 26 doc evidence da frozen tai Gate 25, dong goi manuscript draft, 5 figure
da co provenance va cac bang duoc chuan hoa. Khong co GPU, simulation,
calibration, holdout validation hoac tuning moi.

## Noi dung package

- Manuscript tieng Viet kem English abstract.
- 5 figure Gate 24 da checksum.
- Bang evidence scope, concordance va descriptive metrics.
- Manifest/checksums cho `{count}` artifact.
- Verifier doc lap chi dung file/hash.

## Ket luan duoc phep

{config['claim_lock']['allowed']}

Pozo directionality la `PASS`; quantitative ratio la `MISMATCH`. Package khong
cho phep claim biological Parkinson validation, gene-specific validation,
clinical validation, drug efficacy hay holdout quantitative validation.
"""


def _artifact_record(path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise SubmissionPackageError(f"Missing package artifact: {_relative(path)}")
    return {"path": _relative(path), "role": role, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}


def _write_checksums(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    lines = [f"{record['sha256']}  {record['path']}" for record in sorted(records, key=lambda item: str(item['path']))]
    _write_text(path, "\n".join(lines))


def build_submission_package(
    config_path: Path = DEFAULT_CONFIG,
    package_root: Path = DEFAULT_PACKAGE,
    experiment_root: Path = DEFAULT_EXPERIMENT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Build deterministic Gate 26 submission artifacts from frozen evidence."""
    config = _read_config(config_path)
    manifests, _ = _validate_sources(config)
    tables = {name: ROOT / relative for name, relative in config["tables"].items()}
    concordance = _csv_rows(tables["concordance"])
    _csv_rows(tables["descriptive_metrics"])

    figures_dir = package_root / "figures"
    tables_dir = package_root / "tables"
    for relative in config["figures"]:
        source = ROOT / relative
        if not source.is_file():
            raise SubmissionPackageError(f"Missing Gate 24 figure: {relative}")
        _copy_file(source, figures_dir / source.name)
    _copy_file(tables["concordance"], tables_dir / "table_02_concordance_matrix.csv")
    _copy_file(tables["descriptive_metrics"], tables_dir / "table_03_descriptive_metrics.csv")
    _write_evidence_table(tables_dir / "table_01_evidence_scope.csv")
    _write_text(package_root / "manuscript_vi.md", _manuscript(config, concordance))
    _write_text(package_root / "README.md", _readme(config))
    _write_text(report_path, _report(config, count=0))

    source_paths = [
        config_path,
        *(ROOT / item["path"] for item in config["required_manifests"]),
        *(ROOT / item for item in config["figures"]),
        *tables.values(),
        ROOT / "docs/claims/current_claim_lock.md",
        ROOT / "experiments/gate_25_reproducibility_freeze/manifests/checksums.sha256",
    ]
    generated_paths = [
        package_root / "README.md",
        package_root / "manuscript_vi.md",
        *(figures_dir / Path(item).name for item in config["figures"]),
        tables_dir / "table_01_evidence_scope.csv",
        tables_dir / "table_02_concordance_matrix.csv",
        tables_dir / "table_03_descriptive_metrics.csv",
        report_path,
    ]
    records = [
        *(_artifact_record(path, "source") for path in source_paths),
        *(_artifact_record(path, "package") for path in generated_paths),
    ]
    # Deduplicate source figures and copied figures have different paths, by design.
    manifest_path = experiment_root / "manifests" / "submission_package_manifest.json"
    checksums_path = experiment_root / "manifests" / "checksums.sha256"
    summary_path = experiment_root / "results" / "submission_readiness.json"
    report = _report(config, count=len(records))
    _write_text(report_path, report)
    # The report changed only in its fixed artifact-count placeholder, so refresh its record.
    records = [record for record in records if record["path"] != _relative(report_path)]
    records.append(_artifact_record(report_path, "package"))
    summary = {
        "schema_version": "gate-26-submission-readiness-v1",
        "status": config["package_status"],
        "analysis_only": True,
        "ready_for_internal_review": True,
        "ready_for_biological_parkinson_claim": False,
        "ready_for_gene_specific_claim": False,
        "pozo_directionality": "PASS",
        "pozo_quantitative_ratio": "MISMATCH",
        "figure_count": len(config["figures"]),
        "table_count": 3,
        "evidence_anchor_commit": config["evidence_anchor_commit"],
    }
    _write_json(summary_path, summary)
    records.append(_artifact_record(summary_path, "package"))
    manifest = {
        "schema_version": "gate-26-submission-package-manifest-v1",
        "status": config["package_status"],
        "evidence_anchor_commit": config["evidence_anchor_commit"],
        "analysis_only": True,
        "no_gpu": True,
        "no_simulation": True,
        "no_calibration": True,
        "no_holdout_validation": True,
        "no_tuning": True,
        "claim_lock": config["claim_lock"],
        "boundaries": {
            "biological_parkinson_validation": False,
            "gene_specific_validation": False,
            "clinical_validation": False,
            "drug_validation": False,
            "quantitative_pozo_validation": False,
        },
        "source_gate_statuses": {key: value["status"] for key, value in manifests.items()},
        "artifact_count": len(records),
        "artifacts": records,
        "package_root": _relative(package_root),
        "verification_command": "py -3.12 scripts/verify_gate26_submission_package.py",
    }
    _write_json(manifest_path, manifest)
    records.append(_artifact_record(manifest_path, "package"))
    _write_checksums(checksums_path, records)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--package-root", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        manifest = build_submission_package(args.config, args.package_root, args.experiment_root, args.report)
    except SubmissionPackageError as exc:
        print(f"Status: SUBMISSION_PACKAGE_FAILED\nReason: {exc}")
        return 1
    print(
        f"Status: {manifest['status']}\n"
        f"Artifacts: {manifest['artifact_count']}\n"
        f"Manifest: {args.experiment_root / 'manifests/submission_package_manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
