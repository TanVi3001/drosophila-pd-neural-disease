"""Freeze and verify the compact evidence package used through Gate 24.

This Gate 25 utility is intentionally file-only.  It starts no FlyGym, CUDA,
calibration, holdout, or tuning process.  It verifies existing evidence,
records stable checksums, and produces a compact public reproducibility index.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import tomllib
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT
    / "experiments/gate_25_reproducibility_freeze/configs/reproducibility_freeze.yaml"
)
DEFAULT_OUTPUT = ROOT / "experiments/gate_25_reproducibility_freeze"
DEFAULT_REPORT = ROOT / "docs/reproducibility/gate_25_reproducibility_freeze_report.md"
DEFAULT_README = ROOT / "docs/reproducibility/README.md"


class ReproducibilityFreezeError(ValueError):
    """Raised when an artifact differs from the evidence package contract."""


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
        raise ReproducibilityFreezeError(f"Artifact is outside repository: {path}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReproducibilityFreezeError(f"Invalid JSON artifact: {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise ReproducibilityFreezeError(f"Expected JSON object: {_relative(path)}")
    return value


def _read_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ReproducibilityFreezeError("Gate 25 config must be a YAML mapping")
    return value


def _record(path: Path, *, artifact_id: str, group: str, status: str) -> dict[str, Any]:
    if not path.is_file():
        raise ReproducibilityFreezeError(f"Missing required artifact: {_relative(path)}")
    return {
        "artifact_id": artifact_id,
        "group": group,
        "path": _relative(path),
        "status": status,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _validate_gate_manifests(config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    documents: dict[str, Any] = {}
    for item in config["required_gates"]:
        gate = str(item["gate"])
        path = ROOT / str(item["manifest"])
        document = _read_json(path)
        expected = str(item["expected_status"])
        actual = str(document.get("status", ""))
        if actual != expected:
            raise ReproducibilityFreezeError(
                f"{gate} status is {actual!r}; expected {expected!r}"
            )
        records.append(
            _record(path, artifact_id=gate, group="gate_manifest", status=actual)
        )
        documents[gate] = document

    gate23 = documents["gate_23_pozo_holdout_validation"]
    if gate23.get("quantitative_ratio_match") is not False:
        raise ReproducibilityFreezeError("Gate 23 quantitative mismatch must remain explicit")
    gate24 = documents["gate_24_concordance"]
    for field in ("no_new_simulation", "no_calibration", "no_holdout_validation", "no_tuning"):
        if gate24.get(field) is not True:
            raise ReproducibilityFreezeError(f"Gate 24 must preserve {field}=true")
    if gate24.get("gene_specific_validation") is not False:
        raise ReproducibilityFreezeError("Gate 24 cannot claim gene-specific validation")
    if gate24.get("biological_parkinson_validation") is not False:
        raise ReproducibilityFreezeError("Gate 24 cannot claim biological Parkinson validation")
    return records, documents


def _validate_gate24_sources(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    sources = document.get("source_artifacts")
    if not isinstance(sources, dict) or not sources:
        raise ReproducibilityFreezeError("Gate 24 source_artifacts are missing")
    records: list[dict[str, Any]] = []
    for artifact_id, item in sorted(sources.items()):
        if not isinstance(item, dict):
            raise ReproducibilityFreezeError(f"Invalid Gate 24 source record: {artifact_id}")
        relative = item.get("path")
        expected_hash = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise ReproducibilityFreezeError(f"Incomplete Gate 24 source record: {artifact_id}")
        path = ROOT / relative
        record = _record(path, artifact_id=str(artifact_id), group="gate24_source", status="HASH_VERIFIED")
        if record["sha256"] != expected_hash:
            raise ReproducibilityFreezeError(
                f"Checksum mismatch for Gate 24 source: {relative}"
            )
        records.append(record)
    return records


def _validate_environment(config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pyproject_path = ROOT / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]
    requires_python = str(project["requires-python"])
    if requires_python != ">=3.12,<3.13":
        raise ReproducibilityFreezeError(f"Unexpected Python contract: {requires_python}")
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    if 'python-version: "3.12"' not in workflow or '".[test]"' not in workflow:
        raise ReproducibilityFreezeError("CI workflow does not lock Python 3.12 and test extras")

    records = [
        _record(ROOT / relative, artifact_id=Path(relative).stem, group="environment", status="LOCKED")
        for relative in config["environment_sources"]
    ]
    environment = {
        "schema_version": "gate-25-environment-lock-v1",
        "python_requires": requires_python,
        "core_dependencies": list(project["dependencies"]),
        "optional_dependencies": project.get("optional-dependencies", {}),
        "ci_python_version": "3.12",
        "ci_install": 'python -m pip install -e ".[test]"',
        "line_ending_policy": "text files use LF; PDF files are binary",
        "claim_lock_sha256": _sha256(ROOT / "docs/claims/current_claim_lock.md"),
    }
    return records, environment


def _reject_forbidden_suffixes(records: Iterable[Mapping[str, Any]], config: Mapping[str, Any]) -> None:
    forbidden = {str(value).lower() for value in config["forbidden_artifact_suffixes"]}
    violations = [str(record["path"]) for record in records if Path(str(record["path"])).suffix.lower() in forbidden]
    if violations:
        raise ReproducibilityFreezeError(
            "Large/raw artifacts are not part of the reproducibility freeze: "
            + ", ".join(violations)
        )


def _deduplicate(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        prior = by_path.get(record["path"])
        if prior is None:
            by_path[record["path"]] = record
            continue
        if prior["sha256"] != record["sha256"]:
            raise ReproducibilityFreezeError(f"Conflicting checksum record: {record['path']}")
        prior["artifact_id"] = f"{prior['artifact_id']};{record['artifact_id']}"
        prior["group"] = f"{prior['group']};{record['group']}"
    return [by_path[path] for path in sorted(by_path)]


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _write_inventory(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["artifact_id", "group", "path", "status", "size_bytes", "sha256"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def _report(config: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> str:
    return f"""# Gate 25: Reproducibility Freeze

**Trang thai:** `{config['status']}`

## Muc dich

Gate 25 khoa compact evidence package da duoc su dung den Gate 24. Gate nay chi
doc, kiem tra va bam SHA256 artifact; khong chay GPU, FlyGym simulation,
calibration, holdout validation hoac tuning.

## Evidence anchor

- Ngay khoa: `{config['freeze_date']}`.
- Main evidence anchor: `{config['evidence_anchor_commit']}`.
- Artifact trong inventory: `{len(records)}` tep duy nhat.
- Gate 23 giu ket qua `POZO_HOLDOUT_MISMATCH`.
- Gate 24 giu `gene_specific_validation=false` va
  `biological_parkinson_validation=false`.

## Cach tai lap kiem tra

```powershell
py -3.12 scripts/audit_calibration_targets.py
py -3.12 scripts/run_gate25_reproducibility_freeze.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Neu can tao lai figure Gate 24, cai optional analysis extra bang
`py -3.12 -m pip install -e \".[analysis]\"` truoc khi chay script Gate 24.

## Claim lock

Duoc phep: {config['claim_lock']['allowed']}

Khong duoc dien giai ket qua nay nhu biological Parkinson validation,
gene-specific validation, clinical validation, drug efficacy validation hoac
quantitatively validated holdout model. Pozo chi dat directional concordance;
mismatch dinh luong duoc giu nguyen.

## Tiet kiem dung luong

Inventory khong dua video, checkpoint, rollout NPZ hay artifact raw lon vao
release evidence package. Cac tep raw neu can luu tru phai co checksum/provenance
rieng va co the luu o kho luu tru ngoai repository.
"""


def _readme() -> str:
    return """# Tai lap Gate 25

Thu muc nay ghi lai cach kiem tra tinh toan ven cua evidence package dung cho
Gate 24. No khong chay GPU, FlyGym, calibration, holdout validation hay tuning.

Tu repository root, chay:

```powershell
py -3.12 scripts/audit_calibration_targets.py
py -3.12 scripts/run_gate25_reproducibility_freeze.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Kiem tra `experiments/gate_25_reproducibility_freeze/manifests/checksums.sha256`
bang SHA256 cho moi tep duoc freeze. `freeze_inventory.csv` liet ke scope,
trang thai va checksum cua moi artifact. Khong coi package nay la biological
Parkinson validation hay gene-specific validation.
"""


def run(
    config_path: Path = DEFAULT_CONFIG,
    output_root: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
    readme_path: Path = DEFAULT_README,
) -> dict[str, Any]:
    """Verify existing Gate 11--24 evidence and write Gate 25 artifacts."""
    config = _read_config(config_path)
    required_false = ("run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning")
    if config.get("analysis_only") is not True or any(config.get(field) is not False for field in required_false):
        raise ReproducibilityFreezeError("Gate 25 must remain analysis-only")

    gate_records, documents = _validate_gate_manifests(config)
    source_records = _validate_gate24_sources(documents["gate_24_concordance"])
    environment_records, environment = _validate_environment(config)
    records = _deduplicate([*gate_records, *source_records, *environment_records])
    _reject_forbidden_suffixes(records, config)

    results_dir = output_root / "results"
    manifests_dir = output_root / "manifests"
    inventory_path = results_dir / "freeze_inventory.csv"
    environment_path = results_dir / "environment_lock.json"
    manifest_path = manifests_dir / "reproducibility_freeze_manifest.json"
    checksums_path = manifests_dir / "checksums.sha256"
    _write_inventory(inventory_path, records)
    _write_json(environment_path, environment)
    _write_text(report_path, _report(config, records))
    _write_text(readme_path, _readme())

    generated = [
        _record(config_path, artifact_id="gate25_config", group="gate25_generated", status="LOCKED"),
        _record(inventory_path, artifact_id="freeze_inventory", group="gate25_generated", status="GENERATED"),
        _record(environment_path, artifact_id="environment_lock", group="gate25_generated", status="GENERATED"),
        _record(report_path, artifact_id="gate25_report", group="gate25_generated", status="GENERATED"),
        _record(readme_path, artifact_id="gate25_readme", group="gate25_generated", status="GENERATED"),
    ]
    manifest = {
        "schema_version": "gate-25-reproducibility-freeze-manifest-v1",
        "status": config["status"],
        "freeze_date": config["freeze_date"],
        "evidence_anchor_commit": config["evidence_anchor_commit"],
        "analysis_only": True,
        "no_gpu": True,
        "no_simulation": True,
        "no_calibration": True,
        "no_holdout_validation": True,
        "no_tuning": True,
        "locked_evidence_count": len(records),
        "pozo_quantitative_match": False,
        "gene_specific_validation": False,
        "biological_parkinson_validation": False,
        "artifacts": {
            "inventory": _relative(inventory_path),
            "environment_lock": _relative(environment_path),
            "report": _relative(report_path),
            "readme": _relative(readme_path),
            "checksums": _relative(checksums_path),
        },
        "generated_artifacts": generated,
    }
    _write_json(manifest_path, manifest)
    checksum_records = [*records, *generated, _record(manifest_path, artifact_id="gate25_manifest", group="gate25_generated", status="GENERATED")]
    checksum_lines = [f"{record['sha256']}  {record['path']}" for record in sorted(checksum_records, key=lambda record: record["path"])]
    _write_text(checksums_path, "\n".join(checksum_lines))
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    args = parser.parse_args(argv)
    try:
        manifest = run(args.config, args.output_root, args.report, args.readme)
    except ReproducibilityFreezeError as exc:
        print(f"Status: REPRODUCIBILITY_FREEZE_FAILED\nReason: {exc}")
        return 1
    print(
        f"Status: {manifest['status']}\n"
        f"Locked evidence: {manifest['locked_evidence_count']}\n"
        f"Manifest: {args.output_root / 'manifests/reproducibility_freeze_manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
