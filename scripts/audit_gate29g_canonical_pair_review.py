"""Fail-closed audit for the dual-human Gate29-F canonical-pair review.

This command reads committed lightweight evidence only. It does not launch CUDA,
FlyGym, MuJoCo, calibration, disease execution, or any scientific simulation.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
GATE29F = ROOT / "experiments/gate_29f_canonical_pair_evidence"
EVIDENCE_MANIFEST = GATE29F / "manifests/canonical_pair_evidence_manifest.json"
RAW_CHECKSUMS = GATE29F / "manifests/raw_artifact_checksums.sha256"
PACKAGE_CHECKSUMS = GATE29F / "manifests/package_artifact_checksums.sha256"
COMPARISON = GATE29F / "results/canonical_pair_comparison.json"
METRICS = GATE29F / "results/canonical_pair_metrics.json"
SIGNOFF = (
    ROOT
    / "research/validation/prospective/"
    "gate29f_canonical_pair_independent_review_signoff.json"
)
GATE29G = ROOT / "experiments/gate_29g_canonical_pair_review"
AUDIT_MANIFEST = GATE29G / "manifests/gate29g_review_manifest.json"
AUDIT_CHECKSUMS = GATE29G / "manifests/reviewed_artifact_checksums.sha256"
REPORT = ROOT / "docs/research_design/gate29g_canonical_pair_independent_review.md"

STATUS = "GATE29_CANONICAL_PAIR_INDEPENDENTLY_REVIEWED"
NEXT_STATUS = "READY_FOR_GATE29_H_SCIENTIFIC_TRACE_PREREGISTRATION"
REVIEWED_COMMIT = "b991e14cc281086b349bd0d3d817d2a9bba8ce39"
LOCKED_SIGNALS = {
    "timestamp_s",
    "thorax",
    "joint_positions",
    "actuator_position",
    "contact_found",
}
REQUIRED_ASSERTIONS = {
    "pair_executed_exactly_once",
    "seed_9202_confirmed",
    "two_jobs_confirmed",
    "baseline_returncode_zero",
    "trace_returncode_zero",
    "five_locked_signals_exactly_match",
    "no_retry_confirmed",
    "no_disease_execution_confirmed",
    "no_calibration_confirmed",
    "no_retuning_confirmed",
    "claim_boundary_approved",
}
STABLE_EVIDENCE_FIELDS = (
    "status",
    "pair_id",
    "seed",
    "condition",
    "jobs_executed",
    "baseline_returncode",
    "trace_returncode",
    "execution_state",
    "comparison_status",
    "comparison_rtol",
    "comparison_atol",
    "raw_artifact_count",
    "raw_artifact_total_bytes",
    "raw_artifacts",
    "scientific_jobs",
    "disease_jobs",
    "calibration_run",
    "fitting_run",
    "retuning",
    "dopamine_implemented",
    "biological_validation",
    "claim_scope",
)


class Gate29GError(RuntimeError):
    """A fail-closed Gate29-G review failure."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Gate29GError(f"required file is missing: {path.relative_to(ROOT)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate29GError(f"invalid JSON: {path.relative_to(ROOT)}") from exc
    if not isinstance(value, dict):
        raise Gate29GError(f"JSON object required: {path.relative_to(ROOT)}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_blob(ref: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{ref}:{relative}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise Gate29GError(f"reviewed Git blob is unavailable: {ref}:{relative}")
    return result.stdout


def _checksum_index(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise Gate29GError(f"invalid checksum line: {path.relative_to(ROOT)}")
        digest, relative = parts
        if relative in records:
            raise Gate29GError(f"duplicate checksum path: {relative}")
        records[relative] = digest
    return records


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Gate29GError(message)


def _validate_reviewers(signoff: Mapping[str, Any]) -> list[dict[str, Any]]:
    reviewers = signoff.get("reviewers")
    _require(isinstance(reviewers, list) and len(reviewers) == 2, "exactly two reviewers are required")
    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    for reviewer in reviewers:
        _require(isinstance(reviewer, dict), "reviewer records must be objects")
        name = str(reviewer.get("name", "")).strip()
        role = str(reviewer.get("role", "")).strip()
        _require(name != "" and role != "", "reviewer name and role are required")
        _require(reviewer.get("decision") == "APPROVED", "both reviewer decisions must be APPROVED")
        names.add(name.casefold())
        normalized.append({"name": name, "role": role, "decision": "APPROVED"})
    _require(len(names) == 2, "reviewers must be distinct people")
    review_date = str(signoff.get("review_date", ""))
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise Gate29GError("review_date must use YYYY-MM-DD") from exc
    return normalized


def audit_review() -> dict[str, Any]:
    signoff = _read_json(SIGNOFF)
    current = _read_json(EVIDENCE_MANIFEST)
    comparison = _read_json(COMPARISON)
    metrics = _read_json(METRICS)

    _require(signoff.get("status") == "GATE29F_CANONICAL_PAIR_REVIEW_APPROVED", "review status is not approved")
    _require(signoff.get("decision") == "APPROVED_GATE29F_CANONICAL_PAIR_EVIDENCE", "review decision is not approved")
    _require(signoff.get("no_auto_sign") is True, "no_auto_sign must remain true")
    _require(signoff.get("reviewed_evidence_commit") == REVIEWED_COMMIT, "reviewed evidence commit mismatch")
    _require(signoff.get("pair_id") == "GATE29_CANONICAL_PAIR_V1", "pair ID mismatch")
    _require(signoff.get("seed") == 9202, "reviewed seed mismatch")
    _require(signoff.get("condition") == "healthy", "reviewed condition mismatch")
    reviewers = _validate_reviewers(signoff)

    reviewed_manifest_path = "experiments/gate_29f_canonical_pair_evidence/manifests/canonical_pair_evidence_manifest.json"
    reviewed_raw_index_path = "experiments/gate_29f_canonical_pair_evidence/manifests/raw_artifact_checksums.sha256"
    reviewed_manifest_blob = _git_blob(REVIEWED_COMMIT, reviewed_manifest_path)
    reviewed_raw_index_blob = _git_blob(REVIEWED_COMMIT, reviewed_raw_index_path)
    _require(
        _sha256_bytes(reviewed_manifest_blob)
        == signoff.get("reviewed_gate29f_manifest_git_blob_sha256"),
        "reviewed Gate29-F manifest Git-blob SHA256 mismatch",
    )
    _require(
        _sha256_bytes(reviewed_raw_index_blob)
        == signoff.get("reviewed_raw_checksum_index_git_blob_sha256"),
        "reviewed raw checksum index Git-blob SHA256 mismatch",
    )
    reviewed = json.loads(reviewed_manifest_blob.decode("utf-8"))
    for field in STABLE_EVIDENCE_FIELDS:
        _require(current.get(field) == reviewed.get(field), f"reviewed evidence changed: {field}")

    _require(current.get("status") == "GATE29F_CANONICAL_PAIR_EVIDENCE_LOCKED", "Gate29-F evidence is not locked")
    _require(current.get("jobs_executed") == 2, "canonical pair must contain exactly two jobs")
    _require(current.get("baseline_returncode") == 0 and current.get("trace_returncode") == 0, "canonical jobs did not both pass")
    _require(current.get("execution_state") == "PAIR_COMPLETE", "canonical pair is incomplete")
    _require(current.get("comparison_status") == "TRACE_OBSERVATION_NONPERTURBING_PASS", "non-perturbation comparison failed")
    _require(current.get("raw_artifact_count") == 10, "exactly ten raw artifacts are required")
    _require(current.get("scientific_jobs") == 0 and current.get("disease_jobs") == 0, "scientific firewall was violated")
    for field in ("calibration_run", "fitting_run", "retuning", "dopamine_implemented", "biological_validation"):
        _require(current.get(field) is False, f"scientific firewall was violated: {field}")

    review_assertions = signoff.get("review_assertions")
    _require(isinstance(review_assertions, dict), "review assertions are required")
    _require(set(review_assertions) == REQUIRED_ASSERTIONS, "review assertion set is incomplete")
    _require(all(value is True for value in review_assertions.values()), "all review assertions must be true")
    verification = signoff.get("raw_artifact_verification")
    _require(isinstance(verification, dict), "raw artifact verification is required")
    _require(verification.get("completed") is True, "raw artifact review is incomplete")
    _require(verification.get("method") == "SHA256_MANUAL_REVIEW_AGAINST_GATE29F_INDEX", "raw review method mismatch")
    _require(verification.get("verified_artifact_count") == 10, "raw review did not cover ten artifacts")
    _require(verification.get("mismatch_count") == 0, "raw artifact mismatches were reported")
    _require(verification.get("verified_total_bytes") == current.get("raw_artifact_total_bytes"), "reviewed raw byte count mismatch")

    raw_index = _checksum_index(RAW_CHECKSUMS)
    expected_raw = {item["logical_path"]: item["sha256"] for item in current["raw_artifacts"]}
    _require(raw_index == expected_raw, "raw checksum index does not match Gate29-F manifest")
    package_index = _checksum_index(PACKAGE_CHECKSUMS)
    _require(len(package_index) == 5, "Gate29-F package checksum count mismatch")
    for relative, digest in package_index.items():
        path = ROOT / relative
        _require(path.is_file(), f"Gate29-F package artifact missing: {relative}")
        _require(_sha256(path) == digest, f"Gate29-F package artifact SHA256 mismatch: {relative}")

    comparisons = comparison.get("comparisons")
    _require(isinstance(comparisons, dict) and set(comparisons) == LOCKED_SIGNALS, "locked signal set mismatch")
    for signal, result in comparisons.items():
        _require(result.get("passed") is True, f"locked signal failed: {signal}")
        _require(result.get("max_abs_diff") == 0.0, f"locked signal is not exact: {signal}")
    rows = metrics.get("rows")
    _require(isinstance(rows, list) and len(rows) == 3, "canonical metric set mismatch")
    _require(all(row.get("baseline") == row.get("trace") and row.get("delta") == 0.0 for row in rows), "canonical metrics are not exact")

    _require(signoff.get("scientific_execution_authorized") is False, "scientific execution must remain unauthorized")
    _require(signoff.get("disease_execution_authorized") is False, "disease execution must remain unauthorized")
    _require(signoff.get("gpu_execution_authorized") is False, "GPU execution must remain unauthorized")
    _require(signoff.get("simulation_execution_authorized") is False, "simulation must remain unauthorized")
    _require(signoff.get("approved_next_action") == "GATE29_H_SCIENTIFIC_TRACE_PREREGISTRATION_ONLY", "next action exceeds review scope")

    return {
        "schema_version": "gate29g-canonical-pair-review-audit-v1",
        "status": STATUS,
        "trace_instrumentation_status": "TRACE_INSTRUMENTATION_VALIDATED",
        "next_status": NEXT_STATUS,
        "reviewed_evidence_commit": REVIEWED_COMMIT,
        "pair_id": current["pair_id"],
        "seed": current["seed"],
        "condition": current["condition"],
        "review_date": signoff["review_date"],
        "reviewers": reviewers,
        "reviewer_count": len(reviewers),
        "raw_artifact_count": current["raw_artifact_count"],
        "raw_artifact_total_bytes": current["raw_artifact_total_bytes"],
        "locked_signal_count": len(comparisons),
        "locked_signal_max_abs_diff": max(item["max_abs_diff"] for item in comparisons.values()),
        "package_artifact_count": len(package_index),
        "merge_authorized": True,
        "gpu_executed": False,
        "simulation_executed": False,
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "calibration_run": False,
        "retuning": False,
        "claim_scope": "ENGINEERING_NONPERTURBATION_EVIDENCE_ONLY",
        "biological_validation": False,
    }


def _report(audit: Mapping[str, Any]) -> str:
    reviewer_lines = [
        f"- {item['name']} ({item['role']}): `{item['decision']}`"
        for item in audit["reviewers"]
    ]
    return "\n".join(
        [
            "# Gate 29-G - Duyệt độc lập canonical pair",
            "",
            f"Trạng thái: `{audit['status']}`.",
            "",
            "## Kết quả review",
            "",
            *reviewer_lines,
            f"- Ngày review: `{audit['review_date']}`",
            f"- Evidence commit: `{audit['reviewed_evidence_commit']}`",
            f"- Raw artifacts đã đối chiếu SHA256: `{audit['raw_artifact_count']}/10`",
            f"- Signal đã khóa: `{audit['locked_signal_count']}/5`",
            f"- Sai khác tuyệt đối lớn nhất: `{audit['locked_signal_max_abs_diff']}`",
            "- Pair hoàn thành đúng hai job, không retry.",
            "",
            "## Quyết định",
            "",
            "`TRACE_INSTRUMENTATION_VALIDATED`",
            "",
            f"Bước được phép tiếp theo: `{audit['next_status']}`.",
            "Gate 29-G chỉ cho phép thiết kế và khóa trước protocol Gate 29-H. Gate này không cho phép chạy GPU, simulation hoặc disease job.",
            "",
            "## Giới hạn claim",
            "",
            "Review xác nhận instrumentation không làm thay đổi healthy engineering pair trên năm signal đã khóa. "
            "Kết quả không chứng minh dopamine, không xác nhận mô hình Parkinson sinh học, không phải gene-specific validation và không phải external institutional review.",
            "",
        ]
    )


def write_audit() -> dict[str, Any]:
    audit = audit_review()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_report(audit), encoding="utf-8", newline="\n")
    _write_json(AUDIT_MANIFEST, audit)
    reviewed_paths = (
        SIGNOFF,
        EVIDENCE_MANIFEST,
        RAW_CHECKSUMS,
        PACKAGE_CHECKSUMS,
        COMPARISON,
        METRICS,
        REPORT,
        Path(__file__),
    )
    AUDIT_CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_CHECKSUMS.write_text(
        "".join(
            f"{_sha256(path)}  {path.relative_to(ROOT).as_posix()}\n"
            for path in reviewed_paths
        ),
        encoding="utf-8",
        newline="\n",
    )
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the lightweight review manifest and report")
    args = parser.parse_args()
    audit = write_audit() if args.write else audit_review()
    # Keep CLI output portable on Windows shells that still use cp1252. Files
    # remain UTF-8 with Vietnamese reviewer names preserved.
    print(json.dumps(audit, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
