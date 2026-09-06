"""Validation contract for literature-constrained virtual experiments.

The registry connects a reviewed paper target to a virtual endpoint and a
predeclared runtime.  It is deliberately a preflight layer: validation never
runs FlyGym, creates metrics, or promotes a biological claim.
"""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Mapping


SCHEMA_VERSION = "literature-constrained-experiment-v1"
SUPPORTED_ENDPOINTS = {
    "mean_planar_speed_mm_s",
    "median_planar_speed_mm_s",
    "distance_traveled_mm",
    "activity_time_s",
    "climbing_score",
    "dam_activity",
}
RUNTIME_ENDPOINTS = {"mean_planar_speed_mm_s", "distance_traveled_mm"}
CALIBRATION_ENDPOINTS = {"mean_planar_speed_mm_s", "median_planar_speed_mm_s"}
VALIDATION_ONLY_ENDPOINTS = {"activity_time_s", "climbing_score", "dam_activity"}
ENDPOINT_UNITS = {
    "mean_planar_speed_mm_s": "mm/s",
    "median_planar_speed_mm_s": "mm/s",
    "distance_traveled_mm": "mm",
    "activity_time_s": "s",
}
ALLOWED_ALLOCATIONS = {"calibration", "holdout", "validation_only"}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_BRIDGES = {"identity", "physical_unit_conversion"}
ALLOWED_STATISTICS = {"mean", "median"}

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _issue(
    issues: list[dict[str, str]],
    code: str,
    message: str,
    *,
    severity: str = "error",
    category: str = "protocol",
) -> None:
    issues.append(
        {
            "code": code,
            "message": message,
            "severity": severity,
            "category": category,
        }
    )


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _finite_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _positive_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False
    return number > 0 and float(value) == number


def _nonnegative_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = int(value)
        original = float(value)
    except (TypeError, ValueError):
        return False
    return number >= 0 and original == number


def _normalise_endpoint(value: Any) -> str:
    return _text(value).lower()


def _resolve_path(value: Any, root: Path) -> Path:
    path = Path(_text(value)).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def _parse_notes(value: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _text(value).split(";"):
        if "=" not in item:
            continue
        key, item_value = item.split("=", 1)
        result[key.strip().lower()] = item_value.strip()
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_source(document: Mapping[str, Any], root: Path, issues: list[dict[str, str]]) -> None:
    source = document.get("source")
    if not isinstance(source, Mapping):
        _issue(issues, "MISSING_SOURCE", "source phai la mapping co provenance.", category="target")
        return
    for field in ("paper_id", "record_id", "figure_table"):
        if not _text(source.get(field)):
            _issue(issues, f"MISSING_SOURCE_{field.upper()}", f"source.{field} khong duoc rong.", category="target")
    provenance = source.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        _issue(issues, "MISSING_SOURCE_PROVENANCE", "source.provenance phai la danh sach khong rong.", category="target")
        return
    for item in provenance:
        reference = _text(item)
        if not reference:
            _issue(issues, "EMPTY_PROVENANCE", "Muc provenance khong duoc rong.", category="target")
        elif not reference.startswith(("http://", "https://")) and not _resolve_path(reference, root).is_file():
            _issue(
                issues,
                "MISSING_PROVENANCE_FILE",
                f"Khong tim thay provenance file: {reference}",
                category="target",
            )


def _validate_endpoint(document: Mapping[str, Any], issues: list[dict[str, str]]) -> tuple[str, str]:
    endpoint = document.get("endpoint")
    if not isinstance(endpoint, Mapping):
        _issue(issues, "MISSING_ENDPOINT", "endpoint phai la mapping literature/virtual.")
        return "", ""
    literature = endpoint.get("literature")
    virtual = endpoint.get("virtual")
    bridge = endpoint.get("bridge")
    if not isinstance(literature, Mapping) or not isinstance(virtual, Mapping):
        _issue(issues, "MISSING_ENDPOINT_SIDE", "endpoint.literature va endpoint.virtual phai ton tai.")
        return "", ""
    literature_metric = _text(literature.get("metric"))
    virtual_metric = _normalise_endpoint(virtual.get("metric"))
    literature_unit = _text(literature.get("unit"))
    virtual_unit = _text(virtual.get("unit"))
    literature_statistic = _normalise_endpoint(literature.get("statistic"))
    virtual_statistic = _normalise_endpoint(virtual.get("statistic"))
    if not literature_metric or not literature_unit or literature_statistic not in ALLOWED_STATISTICS:
        _issue(issues, "INVALID_LITERATURE_ENDPOINT", "Literature endpoint phai co metric, unit va statistic mean/median.")
    if virtual_metric not in SUPPORTED_ENDPOINTS:
        _issue(
            issues,
            "UNSUPPORTED_VIRTUAL_ENDPOINT",
            f"Virtual endpoint chua duoc khai bao: {virtual_metric or '<blank>'}",
            category="capability",
        )
    if virtual_metric in ENDPOINT_UNITS and virtual_unit != ENDPOINT_UNITS[virtual_metric]:
        _issue(
            issues,
            "VIRTUAL_ENDPOINT_UNIT_MISMATCH",
            f"{virtual_metric} phai dung don vi {ENDPOINT_UNITS[virtual_metric]}.",
        )
    if virtual_statistic not in ALLOWED_STATISTICS:
        _issue(issues, "INVALID_VIRTUAL_STATISTIC", "Virtual statistic phai la mean hoac median.")
    if literature_statistic and virtual_statistic and literature_statistic != virtual_statistic:
        _issue(
            issues,
            "STATISTIC_MISMATCH",
            "Khong duoc doi median thanh mean hoac mean thanh median.",
        )
    if virtual_metric.startswith("mean_") and literature_statistic == "median":
        _issue(issues, "MEAN_MEDIAN_MISMATCH", "Mean virtual endpoint khong duoc nhan gia tri median.")
    if virtual_metric.startswith("median_") and literature_statistic != "median":
        _issue(issues, "MEDIAN_ENDPOINT_REQUIRES_MEDIAN", "Median virtual endpoint phai co statistic=median.")

    if not isinstance(bridge, Mapping):
        _issue(issues, "MISSING_ENDPOINT_BRIDGE", "endpoint.bridge phai ghi ro cach chuyen assay.")
        return virtual_metric, literature_statistic
    bridge_type = _text(bridge.get("type"))
    if bridge_type not in ALLOWED_BRIDGES:
        _issue(issues, "INVALID_ENDPOINT_BRIDGE", "Bridge chi cho phep identity hoac physical_unit_conversion.")
    elif bridge_type == "identity":
        if literature_metric != virtual_metric or literature_unit != virtual_unit:
            _issue(
                issues,
                "IDENTITY_BRIDGE_MISMATCH",
                "Identity bridge yeu cau metric va unit hai ben giong nhau.",
            )
    elif bridge_type == "physical_unit_conversion":
        factor = _finite_number(bridge.get("factor"))
        if factor is None or factor <= 0:
            _issue(issues, "INVALID_UNIT_CONVERSION_FACTOR", "Physical unit conversion phai co factor huu han duong.")
        if not ("speed" in literature_metric.lower() or "velocity" in literature_metric.lower()):
            _issue(
                issues,
                "SEMANTIC_CONVERSION_NOT_ALLOWED",
                "Chi cho phep doi don vi vat ly trong cung ho speed/velocity; khong doi distance thanh speed.",
            )
        if _text(bridge.get("source_unit")) != literature_unit or _text(bridge.get("target_unit")) != virtual_unit:
            _issue(issues, "UNIT_CONVERSION_ENDPOINT_MISMATCH", "source_unit/target_unit phai khop endpoint hai ben.")
        if not _text(bridge.get("rationale")) or not _text(bridge.get("provenance")):
            _issue(issues, "MISSING_UNIT_CONVERSION_PROVENANCE", "Unit conversion phai co rationale va provenance.", category="target")
    return virtual_metric, literature_statistic


def _validate_target(
    document: Mapping[str, Any],
    root: Path,
    allocation: str,
    virtual_metric: str,
    issues: list[dict[str, str]],
) -> None:
    target = document.get("target")
    if not isinstance(target, Mapping):
        _issue(issues, "MISSING_TARGET_REFERENCE", "Calibration/holdout plan phai co target reference.", category="target")
        return
    target_csv_value = target.get("csv")
    target_csv = _resolve_path(target_csv_value, root)
    if not target_csv.is_file():
        _issue(issues, "MISSING_TARGET_FILE", f"Khong tim thay target CSV: {target_csv}", category="target")
        return
    paper_id = _text(target.get("paper_id"))
    if not paper_id:
        _issue(issues, "MISSING_TARGET_PAPER_ID", "target.paper_id khong duoc rong.", category="target")
        return
    with target_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if _text(row.get("paper_id")) == paper_id]
    if len(rows) != 1:
        _issue(issues, "TARGET_NOT_UNIQUE", f"Target {paper_id} phai khop dung mot row trong {target_csv}.", category="target")
        return
    row = rows[0]
    if _text(row.get("review_status")).lower() != "approved":
        _issue(issues, "TARGET_NOT_APPROVED", "Target phai co review_status=approved.", category="target")
    if _normalise_endpoint(row.get("metric")) != virtual_metric:
        _issue(issues, "TARGET_METRIC_MISMATCH", "Target metric khong khop virtual metric.", category="target")
    notes = _parse_notes(row.get("notes"))
    if notes.get("allocation") != allocation:
        _issue(issues, "TARGET_ALLOCATION_MISMATCH", "Allocation trong target khong khop experiment.", category="target")
    if notes.get("assay_transfer") != "allowed":
        _issue(issues, "TARGET_ASSAY_TRANSFER_NOT_ALLOWED", "Target phai co assay_transfer=allowed.", category="target")
    for key in ("reviewer", "review_date", "sample_unit"):
        if not notes.get(key):
            _issue(issues, f"TARGET_MISSING_{key.upper()}", f"Target thieu {key} trong notes.", category="target")
    if notes.get("review_date") and not _DATE.match(notes["review_date"]):
        _issue(issues, "TARGET_INVALID_REVIEW_DATE", "review_date phai co dang YYYY-MM-DD.", category="target")
    for key in ("value", "variance", "sample_size"):
        if _finite_number(row.get(key)) is None:
            _issue(issues, f"TARGET_NON_NUMERIC_{key.upper()}", f"Target {key} phai la so huu han.", category="target")
    if not _positive_integer(row.get("sample_size")):
        _issue(issues, "TARGET_INVALID_SAMPLE_SIZE", "sample_size phai la so nguyen duong.", category="target")
    if not _text(row.get("doi_pmid")) or not _text(row.get("figure_table")):
        _issue(issues, "TARGET_MISSING_PROVENANCE", "Target phai co DOI/PMID va figure/table.", category="target")


def _validate_runtime(document: Mapping[str, Any], issues: list[dict[str, str]]) -> None:
    runtime = document.get("runtime")
    if not isinstance(runtime, Mapping):
        _issue(issues, "MISSING_RUNTIME", "runtime phai khai bao seeds, steps va timestep.")
        return
    seeds = runtime.get("seeds")
    if not isinstance(seeds, list) or not seeds or any(not _nonnegative_integer(seed) for seed in seeds):
        _issue(issues, "INVALID_SEEDS", "runtime.seeds phai la danh sach seed nguyen khong am.")
    elif len({int(seed) for seed in seeds}) != len(seeds):
        _issue(issues, "DUPLICATE_SEEDS", "runtime.seeds khong duoc trung lap.")
    steps = runtime.get("steps")
    timestep = _finite_number(runtime.get("timestep_s"))
    duration = _finite_number(runtime.get("duration_s"))
    if not _positive_integer(steps):
        _issue(issues, "INVALID_STEPS", "runtime.steps phai la so nguyen duong.")
    if timestep is None or timestep <= 0:
        _issue(issues, "INVALID_TIMESTEP", "runtime.timestep_s phai la so huu han duong.")
    if duration is None or duration <= 0:
        _issue(issues, "INVALID_DURATION", "runtime.duration_s phai la so huu han duong.")
    if timestep is not None and duration is not None and _positive_integer(steps):
        expected = int(steps) * timestep
        if not math.isclose(duration, expected, rel_tol=0.0, abs_tol=1e-12):
            _issue(issues, "DURATION_STEP_MISMATCH", "duration_s phai bang steps*timestep_s.")
    if _text(runtime.get("device")).lower() not in ALLOWED_DEVICES:
        _issue(issues, "INVALID_DEVICE", "runtime.device phai la auto, cuda hoac cpu.")
    for key in ("condition_id", "baseline_condition_id", "stimulus"):
        if not _text(runtime.get(key)):
            _issue(issues, f"MISSING_RUNTIME_{key.upper()}", f"runtime.{key} khong duoc rong.")
    video = runtime.get("video")
    if not isinstance(video, Mapping) or not isinstance(video.get("enabled"), bool):
        _issue(issues, "INVALID_VIDEO_CONFIG", "runtime.video.enabled phai la boolean.")
    elif video.get("enabled"):
        if not _positive_integer(video.get("fps")):
            _issue(issues, "INVALID_VIDEO_FPS", "Video fps phai la so nguyen duong.")
        if not _positive_integer(video.get("width")) or not _positive_integer(video.get("height")):
            _issue(issues, "INVALID_VIDEO_SIZE", "Video width/height phai la so nguyen duong.")


def validate_experiment_plan(document: Mapping[str, Any], *, root: str | Path) -> dict[str, Any]:
    """Validate a registry document without running any simulation."""

    root_path = Path(root).resolve()
    issues: list[dict[str, str]] = []
    if not isinstance(document, Mapping):
        return {
            "status": "INVALID_PROTOCOL",
            "ready_for_runtime": False,
            "issues": [{"code": "DOCUMENT_NOT_MAPPING", "message": "Plan phai la mapping.", "severity": "error", "category": "protocol"}],
        }
    if _text(document.get("schema_version")) != SCHEMA_VERSION:
        _issue(issues, "INVALID_SCHEMA_VERSION", f"schema_version phai la {SCHEMA_VERSION}.")
    if not _text(document.get("experiment_id")):
        _issue(issues, "MISSING_EXPERIMENT_ID", "experiment_id khong duoc rong.")
    if _text(document.get("scientific_scope")) != "organism_level_computational_proxy":
        _issue(issues, "INVALID_SCIENTIFIC_SCOPE", "Scope phai ghi ro organism_level_computational_proxy.")

    allocation = _text(document.get("allocation")).lower()
    if allocation not in ALLOWED_ALLOCATIONS:
        _issue(issues, "INVALID_ALLOCATION", "allocation phai la calibration, holdout hoac validation_only.")
    _validate_source(document, root_path, issues)
    virtual_metric, _ = _validate_endpoint(document, issues)
    _validate_runtime(document, issues)

    proxy = document.get("proxy")
    if not isinstance(proxy, Mapping) or not _text(proxy.get("type")):
        _issue(issues, "MISSING_PROXY", "proxy phai co type va scope.")
    else:
        if _text(proxy.get("scope")) != "organism_level_proxy":
            _issue(issues, "INVALID_PROXY_SCOPE", "Proxy phai giu scope organism_level_proxy.")
        if proxy.get("gene_specific_mapping") is not False:
            _issue(issues, "GENE_SPECIFIC_MAPPING_NOT_PROVEN", "Plan nay khong duoc tu nhan gene-specific mapping.", category="target")

    if virtual_metric in VALIDATION_ONLY_ENDPOINTS and allocation != "validation_only":
        _issue(issues, "VALIDATION_ONLY_ENDPOINT", f"{virtual_metric} chi duoc dung validation_only.", category="capability")
    if allocation == "calibration" and virtual_metric not in CALIBRATION_ENDPOINTS:
        _issue(issues, "ENDPOINT_NOT_CALIBRATION_ELIGIBLE", "Endpoint hien tai khong du dieu kien calibration.", category="capability")
    if allocation == "calibration" and virtual_metric == "distance_traveled_mm":
        _issue(issues, "DISTANCE_NOT_CALIBRATION", "distance_traveled_mm la holdout-only, khong dung de calibration speed.", category="target")
    if virtual_metric not in RUNTIME_ENDPOINTS and allocation != "validation_only":
        _issue(issues, "MISSING_PLATFORM_ENDPOINT", "Virtual runner hien chua export endpoint nay.", category="capability")
    if allocation in {"calibration", "holdout"}:
        _validate_target(document, root_path, allocation, virtual_metric, issues)

    errors = [item for item in issues if item["severity"] == "error"]
    target_waiting = any(item["category"] == "target" for item in errors)
    capability_waiting = any(item["category"] == "capability" for item in errors)
    if not errors:
        status = "VALIDATION_ONLY" if allocation == "validation_only" else "READY_FOR_RUNTIME"
    elif target_waiting:
        status = "WAITING_TARGET_DATA"
    elif capability_waiting:
        status = "WAITING_PLATFORM_CAPABILITY"
    else:
        status = "INVALID_PROTOCOL"
    return {
        "status": status,
        "ready_for_runtime": status == "READY_FOR_RUNTIME",
        "allocation": allocation,
        "virtual_metric": virtual_metric,
        "issues": issues,
        "error_count": len(errors),
        "warning_count": len(issues) - len(errors),
    }


def input_manifest(document: Mapping[str, Any], config_path: Path, validation: Mapping[str, Any]) -> dict[str, Any]:
    """Build a provenance manifest for a validated plan; simulation stays false."""

    return {
        "schema_version": "literature-constrained-experiment-manifest-v1",
        "experiment_id": document.get("experiment_id"),
        "status": validation.get("status"),
        "simulation_executed": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "scientific_scope": document.get("scientific_scope"),
        "validation": dict(validation),
        "plan": dict(document),
        "expected_outputs": document.get("outputs", {}),
        "boundary": {
            "biological_parkinson_validation": False,
            "gene_specific_validation": False,
            "clinical_validation": False,
            "drug_validation": False,
        },
    }


__all__ = [
    "CALIBRATION_ENDPOINTS",
    "RUNTIME_ENDPOINTS",
    "SCHEMA_VERSION",
    "SUPPORTED_ENDPOINTS",
    "VALIDATION_ONLY_ENDPOINTS",
    "input_manifest",
    "validate_experiment_plan",
]
