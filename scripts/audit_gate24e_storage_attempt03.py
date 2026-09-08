"""Freeze the interrupted Gate24E attempt_03 without running or retrying it."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "experiments" / "gate_24e_storage_probe"
ATTEMPT_ROOT = PROBE_ROOT / "attempt_03"
LOG = ATTEMPT_ROOT / "logs" / "storage_probe_attempt_03.log"
AUTHORIZATION = ATTEMPT_ROOT / "manifests" / "attempt_03_authorization.json"
FAILURE_MANIFEST = ATTEMPT_ROOT / "manifests" / "storage_qualification.json"
TOP_LEVEL_MANIFEST = PROBE_ROOT / "manifests" / "storage_qualification.json"
REPORT = ROOT / "docs" / "validation" / "gate24e_attempt03_interruption_audit.md"
FIREWALL = ROOT / "experiments" / "gate_24_prospective_validation" / "manifests" / "holdout_firewall_manifest.json"
ATTEMPT_04 = PROBE_ROOT / "attempt_04"

ATTEMPT_ID = "attempt_03"
PROBE_SEED = 9001
REQUESTED_STEPS = 100000
PLATFORM_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
PROGRESS_PATTERN = re.compile(r"Progress:\s*(\d+)/(\d+)")


class Attempt03AuditError(RuntimeError):
    """Raised when existing evidence does not support the frozen record."""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Attempt03AuditError(f"Missing evidence: {path}") from exc
    if not isinstance(value, dict):
        raise Attempt03AuditError(f"Expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": path.relative_to(ATTEMPT_ROOT).as_posix(),
        "size_bytes": stat.st_size,
        "sha256": _sha256(path),
        "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def inventory_attempt() -> list[dict[str, Any]]:
    if not ATTEMPT_ROOT.is_dir():
        raise Attempt03AuditError(f"Missing attempt directory: {ATTEMPT_ROOT}")
    return [_file_record(path) for path in sorted(ATTEMPT_ROOT.rglob("*")) if path.is_file()]


def parse_log(text: str) -> dict[str, Any]:
    progress = [(int(current), int(total)) for current, total in PROGRESS_PATTERN.findall(text)]
    totals = {total for _, total in progress}
    requested_match = re.search(r"Running healthy:\s*(\d+) FlyGym steps", text)
    requested_steps = int(requested_match.group(1)) if requested_match else None
    simulation_started = requested_match is not None and bool(progress)
    gpu_started = "neurons on cuda" in text and "brain_device=cuda" in text
    last_confirmed = max((current for current, _ in progress), default=None)
    completion_marker = bool(
        requested_steps is not None
        and re.search(rf"Progress:\s*{requested_steps}/{requested_steps}(?:\s|$)", text)
    )
    return {
        "simulation_started": simulation_started,
        "gpu_simulation_started": gpu_started,
        "requested_steps": requested_steps,
        "progress_markers": [current for current, _ in progress],
        "progress_denominators": sorted(totals),
        "last_confirmed_progress_steps": last_confirmed,
        "completion_marker_observed": completion_marker,
        "simulation_completed": completion_marker,
        "keyboard_interrupt_observed": "KeyboardInterrupt" in text,
        "exact_executed_steps_known": False,
        "exact_executed_steps": None,
    }


def build_failure_manifest() -> dict[str, Any]:
    authorization = _json(AUTHORIZATION)
    firewall = _json(FIREWALL)
    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    evidence = parse_log(log_text)

    expected_authorization = {
        "attempt_id": ATTEMPT_ID,
        "platform_commit": PLATFORM_COMMIT,
        "artifact_profile": ARTIFACT_PROFILE,
        "seed": PROBE_SEED,
        "steps": REQUESTED_STEPS,
        "device": "cuda",
        "holdout": "SEALED",
        "scientific_jobs_executed": 0,
        "scientific_batch_authorized": False,
    }
    for key, expected in expected_authorization.items():
        if authorization.get(key) != expected:
            raise Attempt03AuditError(f"Authorization mismatch: {key}={authorization.get(key)!r}")
    expected_evidence = {
        "simulation_started": True,
        "gpu_simulation_started": True,
        "requested_steps": REQUESTED_STEPS,
        "last_confirmed_progress_steps": 40000,
        "completion_marker_observed": False,
        "simulation_completed": False,
        "keyboard_interrupt_observed": True,
    }
    for key, expected in expected_evidence.items():
        if evidence.get(key) != expected:
            raise Attempt03AuditError(f"Log evidence mismatch: {key}={evidence.get(key)!r}")
    if evidence["progress_markers"] != [20000, 40000]:
        raise Attempt03AuditError(f"Unexpected progress markers: {evidence['progress_markers']}")
    if evidence["progress_denominators"] != [REQUESTED_STEPS]:
        raise Attempt03AuditError("Progress denominator does not match requested steps")
    if firewall.get("status") != "SEALED":
        raise Attempt03AuditError(f"Holdout is not sealed: {firewall.get('status')!r}")
    if ATTEMPT_04.exists():
        raise Attempt03AuditError("attempt_04 exists without a new human authorization")

    recorded_at = datetime.now(UTC).isoformat()
    if FAILURE_MANIFEST.is_file():
        previous = _json(FAILURE_MANIFEST)
        recorded_at = str(previous.get("recorded_at_utc") or recorded_at)

    return {
        "schema_version": "gate24e-storage-attempt03-interruption-v1",
        "attempt_id": ATTEMPT_ID,
        "probe_seed": PROBE_SEED,
        "probe_condition": "TECHNICAL_HEALTHY_STORAGE_PROBE",
        "platform_commit": PLATFORM_COMMIT,
        "artifact_profile": ARTIFACT_PROFILE,
        "status": "STORAGE_PROBE_ATTEMPT_03_TECHNICAL_FAILURE",
        "failure_type": "TECHNICAL_INTERRUPTION",
        "failure_stage": "DURING_SIMULATION",
        "exception": "KeyboardInterrupt",
        "simulation_started": True,
        "gpu_simulation_started": True,
        "requested_steps": REQUESTED_STEPS,
        "observed_progress_markers": evidence["progress_markers"],
        "last_confirmed_progress_steps": 40000,
        "exact_executed_steps_known": False,
        "exact_executed_steps": None,
        "completion_marker_observed": False,
        "simulation_completed": False,
        "storage_measurements_valid": False,
        "storage_qualification_valid": False,
        "final_artifact_estimation_allowed": False,
        "storage_failure_classification": "NOT_REACHED_DUE_TO_IN_SIMULATION_INTERRUPTION",
        "attempt_03_consumed": True,
        "attempt_03_retry_allowed": False,
        "automatic_retry": False,
        "attempt_04_authorized": False,
        "scientific_jobs_executed": 0,
        "scientific_results_generated": False,
        "scientific_analysis_allowed": False,
        "probe_included_in_scientific_analysis": False,
        "holdout": "SEALED",
        "holdout_opened": False,
        "tuning_performed": False,
        "posthoc_selection_performed": False,
        "source_evidence_inventory": [_file_record(LOG), _file_record(AUTHORIZATION)],
        "evidence_paths": {
            "log": LOG.relative_to(ROOT).as_posix(),
            "authorization": AUTHORIZATION.relative_to(ROOT).as_posix(),
            "holdout_firewall": FIREWALL.relative_to(ROOT).as_posix(),
        },
        "recorded_at_utc": recorded_at,
        "next_allowed_action": "HUMAN_REVIEW_GATE24E_TECHNICAL_INTERRUPTION",
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def update_top_level(failure: dict[str, Any], complete_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    document = _json(TOP_LEVEL_MANIFEST)
    attempt_01 = dict(document.get("attempt_01") or {})
    attempt_01.update(
        {
            "status": "STORAGE_PROBE_TECHNICAL_FAILURE",
            "failure_stage": "PRE_SIMULATION_CLI_ARGUMENT_PARSE",
            "valid_for_storage_estimation": False,
        }
    )
    attempt_02 = dict(document.get("attempt_02") or {})
    attempt_02.update(
        {
            "status": "STORAGE_PROBE_RETRY_TECHNICAL_FAILURE",
            "failure_stage": "POST_SIMULATION_EXPORT_MEMORY_ERROR",
            "valid_for_storage_estimation": False,
        }
    )
    document.update(
        {
            "schema_version": "gate24e-storage-qualification-history-v3",
            "qualification_status": "GATE24E_STORAGE_NOT_QUALIFIED",
            "current_qualification_status": "GATE24E_STORAGE_NOT_QUALIFIED",
            "current_qualification_reason": "NO_VALID_COMPLETED_STORAGE_PROBE",
            "storage_measurements_valid": False,
            "storage_measurement_status": "NO_VALID_COMPLETED_STORAGE_PROBE",
            "storage_qualification_valid": False,
            "final_artifact_estimation_allowed": False,
            "scientific_jobs_executed": 0,
            "scientific_results_generated": False,
            "holdout": "SEALED",
            "holdout_opened": False,
            "tuning_performed": False,
            "posthoc_selection_performed": False,
            "attempt_01": attempt_01,
            "attempt_02": attempt_02,
            "attempt_03": {
                "status": failure["status"],
                "failure_type": failure["failure_type"],
                "failure_stage": failure["failure_stage"],
                "simulation_started": True,
                "simulation_completed": False,
                "last_confirmed_progress_steps": 40000,
                "exact_executed_steps_known": False,
                "valid_for_storage_estimation": False,
                "attempt_consumed": True,
                "retry_allowed": False,
                "manifest": FAILURE_MANIFEST.relative_to(ROOT).as_posix(),
                "manifest_sha256": _sha256(FAILURE_MANIFEST),
                "inventory": complete_inventory,
            },
            "automatic_retry": False,
            "attempt_04_authorized": False,
            "next_allowed_action": "HUMAN_REVIEW_GATE24E_TECHNICAL_INTERRUPTION",
        }
    )
    document.pop("current_estimate_source", None)
    return document


def build_report(failure: dict[str, Any], inventory: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        f"| `{item['path']}` | {item['size_bytes']} | `{item['sha256']}` | `{item['modified_at_utc']}` |"
        for item in inventory
    )
    return f"""# Gate 24E-S3D: Audit attempt_03 bị gián đoạn

## Kết luận

`attempt_03` là một technical storage probe đã khởi chạy nhưng bị ngắt trong
simulation. Trạng thái được khóa là
`ATTEMPT_03_TECHNICAL_FAILURE_RECORDED`. Đây không phải lỗi khoa học, lỗi mô
hình bệnh, lỗi memory-safe exporter hay kết luận về khả năng lưu trữ.

## Bằng chứng runtime

- Runtime commit: `{PLATFORM_COMMIT}`.
- Artifact profile: `{ARTIFACT_PROFILE}`.
- Probe seed: `{PROBE_SEED}`; không thuộc scientific seeds.
- CUDA/GPU đã thực sự được dùng; log ghi `138639 neurons on cuda`.
- Simulation được yêu cầu `{REQUESTED_STEPS}` steps.
- Các marker quan sát được: `20000/100000`, `40000/100000`.
- `last_confirmed_progress_steps=40000`; không khẳng định chính xác chỉ có
  40000 steps đã chạy.
- Không có marker `100000/100000`.
- Traceback kết thúc bằng `KeyboardInterrupt` trong `controller.step(...)`.
- Phân loại: `TECHNICAL_INTERRUPTION`, stage `DURING_SIMULATION`.

## Inventory đã đóng băng

| Đường dẫn tương đối | Bytes | SHA256 | Modified UTC |
|---|---:|---|---|
{rows}

## Ranh giới diễn giải

- Simulation không hoàn tất; export/storage qualification chưa được đạt tới.
- Storage measurements, storage qualification và final artifact estimation đều
  không hợp lệ.
- Không ngoại suy dung lượng cho 25 jobs và không dùng lại ước lượng attempt_01
  hoặc attempt_02.
- Không có scientific result; probe này không được đưa vào phân tích locomotion.
- Scientific jobs vẫn là `0`; không tuning và không post-hoc selection.
- Holdout vẫn `SEALED`.
- `attempt_03` đã consumed, không được retry tự động hoặc thủ công theo quyền
  hiện tại.
- `attempt_04` chưa được tạo hoặc cấp quyền.

Hành động tiếp theo duy nhất: `HUMAN_REVIEW_GATE24E_TECHNICAL_INTERRUPTION`.
"""


def freeze_attempt() -> dict[str, Any]:
    failure = build_failure_manifest()
    _write_json(FAILURE_MANIFEST, failure)
    complete_inventory = inventory_attempt()
    _write_json(TOP_LEVEL_MANIFEST, update_top_level(failure, complete_inventory))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(failure, complete_inventory), encoding="utf-8")
    return {
        "status": "ATTEMPT_03_TECHNICAL_FAILURE_RECORDED",
        "attempt_id": ATTEMPT_ID,
        "last_confirmed_progress_steps": 40000,
        "simulation_completed": False,
        "storage_qualification_valid": False,
        "scientific_jobs_executed": 0,
        "holdout": "SEALED",
        "attempt_03_consumed": True,
        "attempt_03_retry_allowed": False,
        "attempt_04_authorized": False,
        "gpu_executed_by_audit": False,
        "simulation_executed_by_audit": False,
        "next_allowed_action": "HUMAN_REVIEW_GATE24E_TECHNICAL_INTERRUPTION",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the frozen manifests and report.")
    args = parser.parse_args(argv)
    try:
        result = freeze_attempt() if args.write else build_failure_manifest()
    except (Attempt03AuditError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ATTEMPT_03_AUDIT_INVALID", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
