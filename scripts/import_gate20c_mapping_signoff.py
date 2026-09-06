"""Import and audit Gate 20C mapping evidence without inferring identifiers."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONDITION_IDS = ("alpha_synuclein", "pink1", "parkin", "dj1", "lrrk2")
MANUAL_ROOT = ROOT / "research/disease_mapping/manual_imports"
QUERY_ROOT = ROOT / "research/disease_mapping/query_plans"
EXPORT_ROOT = ROOT / "research/disease_mapping/exports"
REVIEW_PATH = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"
ROOT_AUDIT_PATH = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
MAPPING_STATUS_PATH = ROOT / "research/disease_mapping/mapping_status.csv"
CONFIG_ROOT = ROOT / "configs/conditions"
OUTPUT_ROOT = ROOT / "experiments/gate_20c_mapping_acquisition"
SUMMARY_PATH = OUTPUT_ROOT / "results/gate20c_mapping_acquisition_summary.json"
MANIFEST_PATH = OUTPUT_ROOT / "manifests/gate20c_mapping_acquisition_manifest.json"
REPORT_PATH = ROOT / "docs/disease_mapping/gate_20c_mapping_acquisition_report.md"

IMPORT_NAMES = ("codex_export.csv", "flywire_export.tsv", "paper_mapping_evidence.csv")
APPROVED_DECISIONS = {
    "APPROVED",
    "APPROVED_FOR_CLASS_LEVEL_EXPLORATORY",
}
SIGNOFF_DECISIONS = APPROVED_DECISIONS | {
    "PENDING_HUMAN_SIGNOFF",
    "REJECTED",
}
MAPPING_LEVELS = {
    "GENE_SPECIFIC",
    "CLASS_LEVEL_EXPLORATORY_ONLY",
    "ORGANISM_LEVEL_PROXY_ONLY",
    "PAN_NEURONAL_ORGANISM_LEVEL",
    "WHOLE_ANIMAL_ORGANISM_LEVEL",
    "DRIVER_OR_CLASS_LEVEL",
    "WAITING_VNC_CONNECTOME_MAPPING",
    "UNRESOLVED",
    "NOT_MAPPABLE_FROM_PAPER",
    "NOT_MAPPABLE_TO_CURRENT_CONNECTOME",
}
PLACEHOLDER_VALUES = {
    "",
    "[]",
    "{}",
    "none",
    "null",
    "not_cell_specific",
    "not_a_single_neuron",
    "todo_root_id",
    "fake_root_id",
    "synthetic_root",
    "tbd_root",
    "mock_root",
    "000000",
}
REQUIRED_COLUMNS = {
    "condition_id",
    "root_id",
    "edge_id",
    "cell_type",
    "cell_class",
    "driver_scope",
    "anatomy_scope",
    "connectome_name",
    "connectome_version",
    "source_url",
    "query_string",
    "query_date",
    "exported_by",
    "notes",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [
            {str(key).strip(): str(value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _is_identifier(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in PLACEHOLDER_VALUES:
        return False
    if normalized.startswith("not_") or normalized.startswith("no_"):
        return False
    return bool(value.strip())


def _unique_identifiers(rows: Iterable[Mapping[str, str]]) -> tuple[list[str], list[str]]:
    roots: set[str] = set()
    edges: set[str] = set()
    for row in rows:
        root_id = row.get("root_id", "").strip()
        edge_id = row.get("edge_id", "").strip()
        if _is_identifier(root_id):
            roots.add(root_id)
        if _is_identifier(edge_id):
            edges.add(edge_id)
    return sorted(roots), sorted(edges)


def _config_path(condition_id: str) -> Path:
    return CONFIG_ROOT / f"{condition_id}.template.yaml"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _load_config(condition_id: str) -> dict[str, Any]:
    path = _config_path(condition_id)
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def _existing_condition(condition_id: str) -> dict[str, Any]:
    review = _load_json(EXPORT_ROOT / condition_id / "mapping_review.json")
    source = _load_json(EXPORT_ROOT / condition_id / "source_manifest.json")
    export_path = EXPORT_ROOT / condition_id / "mapping_export.csv"
    export_rows = _read_csv(export_path) if export_path.is_file() else []
    row = export_rows[0] if export_rows else {}
    return {
        "review": review,
        "source": source,
        "export": row,
        "export_path": export_path,
    }


def _manual_files(condition_id: str) -> list[Path]:
    directory = MANUAL_ROOT / condition_id
    return [directory / name for name in IMPORT_NAMES if (directory / name).is_file()]


def _read_manual_rows(paths: Iterable[Path]) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for path in paths:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=delimiter)
                columns = {str(column or "").strip() for column in reader.fieldnames or []}
                missing = sorted(REQUIRED_COLUMNS - columns)
                if missing:
                    errors.append(f"{_relative(path)} thiếu cột: {', '.join(missing)}")
                    continue
                rows.extend(
                    {
                        str(key).strip(): str(value or "").strip()
                        for key, value in row.items()
                    }
                    for row in reader
                )
        except (OSError, csv.Error, UnicodeError) as exc:
            errors.append(f"{_relative(path)} không đọc được: {exc}")
    return rows, errors


def _signoff(condition_id: str) -> tuple[dict[str, Any], list[str], Path | None]:
    path = MANUAL_ROOT / condition_id / "reviewer_signoff.json"
    if not path.is_file():
        return {}, ["chưa có reviewer_signoff.json"], None
    try:
        document = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"reviewer_signoff.json không đọc được: {exc}"], path
    errors: list[str] = []
    declared = str(document.get("condition_id") or document.get("condition") or "").strip()
    if declared != condition_id:
        errors.append("condition_id trong signoff không khớp thư mục")
    decision = str(document.get("decision", "")).strip()
    if decision not in SIGNOFF_DECISIONS:
        errors.append("decision không thuộc tập giá trị được phép")
    mapping_level = str(document.get("mapping_level", "")).strip()
    if mapping_level not in MAPPING_LEVELS:
        errors.append("mapping_level không thuộc tập giá trị được phép")
    reviewer_1 = str(document.get("reviewer_1", "")).strip()
    reviewer_2 = str(document.get("reviewer_2", "")).strip()
    review_date = str(document.get("review_date") or document.get("date") or "").strip()
    if not reviewer_1:
        errors.append("thiếu reviewer_1")
    if not reviewer_2:
        errors.append("thiếu reviewer_2")
    if not _valid_date(review_date):
        errors.append("review_date phải có dạng YYYY-MM-DD")
    if not str(document.get("allowed_rollout_scope", "")).strip():
        errors.append("thiếu allowed_rollout_scope")
    if "gene_specific_mapping" not in document:
        errors.append("thiếu gene_specific_mapping")
    human_notes = str(document.get("human_notes") or document.get("human_review_notes") or "").strip()
    if not human_notes:
        errors.append("thiếu human_notes")
    return document, errors, path


def _metadata_errors(condition_id: str, rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["không có dòng mapping có thể kiểm tra"]
    for index, row in enumerate(rows, start=2):
        if row.get("condition_id", "") != condition_id:
            errors.append(f"dòng {index}: condition_id không khớp")
        if not (_is_identifier(row.get("root_id", "")) or _is_identifier(row.get("edge_id", ""))):
            errors.append(f"dòng {index}: thiếu root_id/edge_id thật")
        if not (row.get("cell_type") or row.get("cell_class")):
            errors.append(f"dòng {index}: thiếu cell_type/cell_class")
        if not (row.get("driver_scope") or row.get("anatomy_scope")):
            errors.append(f"dòng {index}: thiếu driver_scope/anatomy_scope")
        for field in ("connectome_name", "connectome_version", "source_url", "query_string", "query_date", "exported_by"):
            if not row.get(field):
                errors.append(f"dòng {index}: thiếu {field}")
        if row.get("query_date") and not _valid_date(row["query_date"]):
            errors.append(f"dòng {index}: query_date không hợp lệ")
        source_sha = row.get("source_sha256", "").strip()
        if not source_sha:
            errors.append(f"dòng {index}: thiếu source_sha256 của artifact nguồn")
        elif not re.fullmatch(r"[0-9a-fA-F]{64}", source_sha):
            errors.append(f"dòng {index}: source_sha256 không phải SHA-256")
    return errors


def _config_errors(condition_id: str, root_ids: list[str], edge_ids: list[str]) -> list[str]:
    config = _load_config(condition_id)
    errors: list[str] = []
    if not config:
        return ["condition YAML không tồn tại hoặc không đọc được"]
    config_targets = list(config.get("target_neurons") or []) + list(config.get("target_edges") or [])
    if not config_targets:
        errors.append("condition YAML chưa có target_neurons/target_edges")
    if not config.get("provenance"):
        errors.append("condition YAML chưa có provenance")
    if not config.get("burden_curve"):
        errors.append("condition YAML chưa có burden_curve")
    if not (config.get("full_burden") or config.get("perturbation_rule")):
        errors.append("condition YAML chưa có full_burden/perturbation_rule")
    expected = set(str(item) for item in root_ids + edge_ids)
    if expected and not expected.intersection(str(item) for item in config_targets):
        errors.append("target trong YAML không khớp mapping import")
    return errors


def _condition_result(condition_id: str) -> dict[str, Any]:
    existing = _existing_condition(condition_id)
    paths = _manual_files(condition_id)
    rows, table_errors = _read_manual_rows(paths)
    signoff, signoff_errors, signoff_path = _signoff(condition_id)
    roots, edges = _unique_identifiers(rows)
    metadata_errors = _metadata_errors(condition_id, rows) if paths else []
    decision = str(signoff.get("decision", "")).strip() or str(
        existing["review"].get("decision") or existing["source"].get("decision") or "PENDING_HUMAN_SIGNOFF"
    )
    mapping_level = str(signoff.get("mapping_level", "")).strip() or str(
        existing["review"].get("mapping_level") or "UNRESOLVED"
    )
    reviewer_2 = str(signoff.get("reviewer_2", "")).strip() or str(
        existing["review"].get("reviewer_2") or existing["source"].get("reviewer_2") or ""
    )
    review_date = str(signoff.get("review_date") or signoff.get("date") or "").strip() or str(
        existing["review"].get("review_date") or existing["source"].get("review_date") or ""
    )
    config_errors = _config_errors(condition_id, roots, edges) if paths and not table_errors and not metadata_errors and decision in APPROVED_DECISIONS else []
    all_errors = table_errors + metadata_errors + signoff_errors + config_errors
    if not paths:
        status = "BLOCKED_NO_MANUAL_IMPORT"
        blockers = [
            "chưa có Codex/FlyWire/paper mapping export cục bộ",
            "chưa có reviewer_signoff.json cho condition",
            "Gate 20B chỉ cung cấp provenance reference-only với 0 identifier",
        ]
        approved = False
    elif decision not in APPROVED_DECISIONS:
        status = "BLOCKED_SIGNOFF_NOT_APPROVED"
        blockers = all_errors or ["reviewer signoff chưa quyết định APPROVED"]
        approved = False
    elif all_errors:
        status = "BLOCKED_INVALID_OR_INCOMPLETE_EVIDENCE"
        blockers = all_errors
        approved = False
    else:
        status = "APPROVED"
        blockers = []
        approved = True
    return {
        "condition_id": condition_id,
        "manual_import_files": [
            {"path": _relative(path), "sha256": _sha256(path)} for path in paths
        ],
        "signoff_file": (
            {"path": _relative(signoff_path), "sha256": _sha256(signoff_path)}
            if signoff_path
            else None
        ),
        "import_row_count": len(rows),
        "root_id_count": len(roots),
        "edge_id_count": len(edges),
        "mapping_identifier_count": len(roots) + len(edges),
        "root_ids": roots,
        "edge_ids": edges,
        "decision": decision,
        "mapping_level": mapping_level,
        "reviewer_2": reviewer_2,
        "review_date": review_date,
        "status": status,
        "approved_condition": approved,
        "config_ready": not config_errors if paths and decision in APPROVED_DECISIONS else False,
        "blockers": blockers,
        "existing_gate20b_export": _relative(existing["export_path"]),
        "no_identifier_inference": True,
    }


def _source_inputs(condition_results: list[Mapping[str, Any]]) -> dict[str, str]:
    paths = [REVIEW_PATH, ROOT_AUDIT_PATH, MAPPING_STATUS_PATH]
    paths.extend(_config_path(condition) for condition in CONDITION_IDS)
    for condition in CONDITION_IDS:
        package = EXPORT_ROOT / condition
        paths.extend(package / name for name in ("mapping_export.csv", "mapping_review.json", "source_manifest.json"))
    for result in condition_results:
        paths.extend(
            ROOT / item["path"] for item in result.get("manual_import_files", [])
        )
        signoff = result.get("signoff_file")
        if signoff:
            paths.append(ROOT / signoff["path"])
    hashes: dict[str, str] = {}
    for path in paths:
        if path.is_file():
            hashes[_relative(path)] = _sha256(path)
    return dict(sorted(hashes.items()))


def _write_condition_table(condition_results: list[Mapping[str, Any]]) -> Path:
    path = OUTPUT_ROOT / "results/condition_mapping_acquisition.csv"
    fields = [
        "condition_id",
        "status",
        "approved_condition",
        "mapping_level",
        "mapping_identifier_count",
        "root_id_count",
        "edge_id_count",
        "import_row_count",
        "reviewer_2",
        "review_date",
        "blockers",
    ]
    rows = []
    for result in condition_results:
        row = dict(result)
        row["blockers"] = "; ".join(str(item) for item in result["blockers"])
        rows.append(row)
    _write_csv(path, rows, fields)
    return path


def _build_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Gate 20C - Mapping acquisition và human signoff",
        "",
        f"**Trạng thái:** `{summary['status']}`",
        "",
        "## Kết quả hiện tại",
        "",
        f"- Approved condition: `{summary['approved_condition_count']}/{summary['reviewed_condition_count']}`.",
        f"- Condition đã được kiểm tra trong package: `{summary['reviewed_condition_count']}/5`.",
        f"- Disease mapping readiness: `{summary['disease_mapping_status']}`.",
        "- Không chạy GPU, simulation, calibration hoặc tuning.",
        "- Không sửa raw metrics hay healthy core.",
        "- Không suy ra root ID/edge ID từ gene, driver, phenotype hoặc tên tế bào.",
        "",
        "## Bảng condition",
        "",
        "| Condition | Import thật | Identifier | Signoff | Kết luận |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for result in summary["condition_statuses"].values():
        evidence = "có" if result["manual_import_files"] else "không"
        identifiers = result["mapping_identifier_count"]
        signoff = result["decision"]
        lines.append(
            f"| `{result['condition_id']}` | {evidence} | `{identifiers}` | `{signoff}` | `{result['status']}` |"
        )
    lines.extend(
        [
            "",
            "## Có thể đạt 5/5 approved ngay không?",
            "",
            "**Không.** Parkin hiện có filtered export 330 root ID ở mức DAN/dopaminergic từ FlyWire để review, nhưng chưa có reviewer signoff hợp lệ; bốn condition còn lại chưa có export tương ứng. Vì vậy hệ thống giữ `0/5`, không tạo ID tổng hợp và không nâng trạng thái bằng suy luận.",
            "",
            "Để một condition được tính là approved, cần đồng thời có identifier thật, cell type/class, driver hoặc anatomy scope, connectome version, source URL, query/export source, SHA-256 của artifact, reviewer_2, review_date, signoff hợp lệ và YAML condition đã có target/provenance/burden tương thích.",
            "",
            "## Dữ liệu cần bổ sung",
            "",
            "1. Một file `codex_export.csv`, `flywire_export.tsv` hoặc `paper_mapping_evidence.csv` cho từng condition, theo đúng schema trong query plan.",
            "2. `reviewer_signoff.json` do reviewer thật điền, không dùng tên/ngày giả.",
            "3. SHA-256 của export và provenance của nguồn; không commit nguyên dump lớn nếu chỉ cần filtered export.",
            "4. Mapping VNC/motor-neuron tương thích cho LRRK2 nếu muốn mở rộng ngoài brain-only scope.",
            "",
            "## Gate kế tiếp",
            "",
            "Chỉ sau khi có import hợp lệ và signoff, chạy lại script này với kiểm tra audit. Nếu có condition approved nhưng YAML còn thiếu burden/provenance, condition vẫn bị chặn khỏi disease rollout.",
            "",
            "## Ranh giới khoa học",
            "",
            "Gate 20C chỉ là cổng thu nhận và kiểm tra provenance mapping. Nó không phải xác nhận cơ chế bệnh, không tạo disease metrics, không thay thế thí nghiệm trên ruồi thật và không phải công cụ chẩn đoán hay đánh giá thuốc.",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_summary(condition_results: list[Mapping[str, Any]], table_path: Path) -> dict[str, Any]:
    approved = sum(bool(result["approved_condition"]) for result in condition_results)
    reviewed = len(condition_results)
    status = "MAPPING_ACQUISITION_READY" if approved else "MAPPING_ACQUISITION_BLOCKED"
    return {
        "schema_version": "gate-20c-mapping-acquisition-summary-v1",
        "created_at_utc": _now(),
        "status": status,
        "approved_condition_count": approved,
        "reviewed_condition_count": reviewed,
        "all_five_conditions_approved": approved == 5,
        "disease_mapping_status": "DISEASE_MAPPING_READY" if approved else "DISEASE_MAPPING_BLOCKED",
        "condition_statuses": {str(item["condition_id"]): dict(item) for item in condition_results},
        "condition_table": _relative(table_path),
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "no_root_id_inference": True,
        "data_fabricated": False,
        "scientific_scope": "Mapping acquisition and human signoff gate; no biological disease validation.",
    }


def run(*, apply_approved: bool = False) -> int:
    for condition in CONDITION_IDS:
        (MANUAL_ROOT / condition).mkdir(parents=True, exist_ok=True)
    QUERY_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.joinpath("results").mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.joinpath("manifests").mkdir(parents=True, exist_ok=True)
    condition_results = [_condition_result(condition) for condition in CONDITION_IDS]
    if apply_approved and any(item["approved_condition"] for item in condition_results):
        raise NotImplementedError(
            "Primary-file promotion is intentionally a separate reviewed operation; "
            "this importer only stages and audits evidence."
        )
    table_path = _write_condition_table(condition_results)
    summary = _build_summary(condition_results, table_path)
    report_text = _build_report(summary)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8", newline="\n")
    _write_json(SUMMARY_PATH, summary)
    manifest = {
        "schema_version": "gate-20c-mapping-acquisition-manifest-v1",
        "created_at_utc": _now(),
        "status": summary["status"],
        "summary": _relative(SUMMARY_PATH),
        "report": _relative(REPORT_PATH),
        "condition_table": _relative(table_path),
        "source_inputs_sha256": _source_inputs(condition_results),
        "large_external_dumps_committed": False,
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "no_root_id_inference": True,
        "data_fabricated": False,
    }
    _write_json(MANIFEST_PATH, manifest)
    print(f"Status: {summary['status']}")
    print(f"Approved condition: {summary['approved_condition_count']}/{summary['reviewed_condition_count']}")
    print(f"Summary: {SUMMARY_PATH.resolve()}")
    print(f"Report: {REPORT_PATH.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply-approved",
        action="store_true",
        help="Reserved for a separately reviewed promotion operation; never infers or fabricates IDs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(apply_approved=args.apply_approved)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, json.JSONDecodeError, yaml.YAMLError, NotImplementedError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
