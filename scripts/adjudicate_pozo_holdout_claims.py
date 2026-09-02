"""Create the Gate 14C Pozo holdout interpretation and claim lock.

This script is intentionally read-only with respect to Gate 14B inputs. It
does not run FlyGym, calibration, tuning, or any new simulation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GATE_14B_ROOT = REPOSITORY_ROOT / "experiments" / "gate_14b_pozo_holdout_validation"
GATE_14C_ROOT = REPOSITORY_ROOT / "experiments" / "gate_14c_holdout_adjudication"

GATE_14B_SUMMARY = (
    GATE_14B_ROOT / "results" / "pozo_holdout_result_summary.json"
)
GATE_14B_MANIFEST = GATE_14B_ROOT / "manifests" / "pozo_holdout_manifest.json"
GATE_14A_PROTOCOL = (
    REPOSITORY_ROOT
    / "experiments"
    / "gate_14a_pozo_holdout_protocol"
    / "configs"
    / "pozo_holdout_protocol.yaml"
)
GATE_13B_CONFIG = (
    REPOSITORY_ROOT
    / "experiments"
    / "gate_13b_chen_ratio_calibration"
    / "configs"
    / "calibrated_alpha_synuclein_proxy.yaml"
)
GATE_13C_MANIFEST = (
    REPOSITORY_ROOT
    / "experiments"
    / "gate_13c_calibrated_confirmation"
    / "manifests"
    / "calibrated_confirmation_manifest.json"
)

SUMMARY_PATH = GATE_14C_ROOT / "results" / "holdout_adjudication_summary.json"
CLAIM_TABLE_PATH = GATE_14C_ROOT / "results" / "claim_lock_table.csv"
MANIFEST_PATH = GATE_14C_ROOT / "manifests" / "holdout_adjudication_manifest.json"
REPORT_PATH = (
    REPOSITORY_ROOT / "docs" / "holdout" / "gate_14c_holdout_adjudication_report.md"
)
CLAIM_DOC_PATH = REPOSITORY_ROOT / "docs" / "claims" / "current_claim_lock.md"

FINAL_STATUS = "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _verify_gate14b_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    paths = [
        GATE_14B_SUMMARY,
        GATE_14B_MANIFEST,
        GATE_14A_PROTOCOL,
        GATE_13B_CONFIG,
        GATE_13C_MANIFEST,
    ]
    for path in paths:
        _require(path.is_file(), f"Missing required source: {_relative(path)}")

    gate14b_summary = _read_json(GATE_14B_SUMMARY)
    gate14b_manifest = _read_json(GATE_14B_MANIFEST)
    gate14a_protocol = _read_yaml(GATE_14A_PROTOCOL)
    gate13b_config = _read_yaml(GATE_13B_CONFIG)
    gate13c_manifest = _read_json(GATE_13C_MANIFEST)

    _require(
        gate14b_summary.get("execution_status") == "POZO_HOLDOUT_RUNTIME_PASS",
        "Gate 14B execution status is not POZO_HOLDOUT_RUNTIME_PASS",
    )
    _require(gate14b_summary.get("planned_runs") == 12, "Gate 14B planned_runs must be 12")
    _require(
        gate14b_summary.get("successful_runs") == 12,
        "Gate 14B successful_runs must be 12",
    )
    _require(gate14b_summary.get("condition_id") == "pink1", "Gate 14B condition must be pink1")
    _require(
        gate14b_summary.get("proxy_scope") == "organism_level_proxy",
        "Gate 14B must be organism-level proxy scope",
    )
    _require(
        gate14b_summary.get("gene_specific_mapping") is False,
        "Gate 14B must not claim gene-specific mapping",
    )
    locked = gate14b_summary.get("locked_parameter", {})
    _require(
        math.isclose(float(locked.get("proxy_burden_level")), 0.5, abs_tol=1e-12),
        "Gate 14B burden must remain locked at 0.5",
    )
    for key in (
        "no_parameter_reselection",
        "no_pozo_tuning",
        "no_calibration_run",
        "no_biological_validation_claim",
    ):
        _require(gate14b_summary.get(key) is True, f"Gate 14B flag {key} must be true")

    for key in (
        "no_parameter_reselection",
        "no_pozo_tuning",
        "no_calibration_run",
        "no_gene_specific_mapping",
        "no_biological_validation_claim",
    ):
        _require(gate14b_manifest.get(key) is True, f"Gate 14B manifest flag {key} must be true")

    # Verify the raw Gate 14B result hashes before producing the adjudication.
    manifest_hash_fields = {
        "config_sha256": GATE_14B_ROOT / "configs" / "pozo_holdout_run_config.yaml",
        "metrics_csv_sha256": GATE_14B_ROOT / "results" / "pozo_holdout_metrics.csv",
        "metrics_json_sha256": GATE_14B_ROOT / "results" / "pozo_holdout_metrics.json",
        "summary_csv_sha256": GATE_14B_ROOT / "results" / "pozo_holdout_summary.csv",
        "result_summary_sha256": GATE_14B_SUMMARY,
    }
    for field, path in manifest_hash_fields.items():
        _require(path.is_file(), f"Missing Gate 14B artifact: {_relative(path)}")
        _require(
            _sha256(path) == gate14b_manifest.get(field),
            f"Gate 14B checksum mismatch for {_relative(path)}",
        )

    _require(
        gate14a_protocol.get("status") == "READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT",
        "Gate 14A protocol is not locked for Gate 14B",
    )
    protocol_lock = gate14a_protocol.get("locked_calibration", {})
    _require(
        math.isclose(float(protocol_lock.get("selected_value")), 0.5, abs_tol=1e-12),
        "Gate 14A selected burden is not 0.5",
    )
    _require(protocol_lock.get("no_parameter_reselection") is True, "Gate 14A allows reselection")
    _require(protocol_lock.get("no_pozo_tuning") is True, "Gate 14A allows Pozo tuning")

    _require(
        gate13b_config.get("status") == "CHEN_RATIO_CALIBRATED",
        "Gate 13B calibrated config is not active",
    )
    gate13b_selected = gate13b_config.get("selected_parameter", {}).get("selected_value")
    _require(
        math.isclose(float(gate13b_selected), 0.5, abs_tol=1e-12),
        "Gate 13B selected burden is not 0.5",
    )
    _require(gate13b_config.get("gene_specific_mapping") is False, "Gate 13B is gene-specific")
    _require(
        gate13c_manifest.get("status") == "CHEN_CALIBRATED_CONFIRMATION_PASS",
        "Gate 13C confirmation is not PASS",
    )
    _require(gate13c_manifest.get("no_pozo") is True, "Gate 13C unexpectedly used Pozo")
    _require(gate13c_manifest.get("no_pink1") is True, "Gate 13C unexpectedly used PINK1")

    return gate14b_summary, gate14b_manifest, gate14a_protocol, gate13b_config, gate13c_manifest


def _claim_rows() -> list[dict[str, str]]:
    return [
        {
            "claim": "Chen calibration",
            "status": "allowed",
            "allowed_wording": "Chen-only ratio calibration selected proxy_burden_level 0.5",
            "forbidden_wording": "perfect calibration",
            "evidence_source": "Gate 13B calibrated config",
            "notes": "Chen là calibration source; không dùng Pozo để tune.",
        },
        {
            "claim": "Chen confirmation",
            "status": "allowed",
            "allowed_wording": "Independent seeded rerun confirmed the locked parameter behavior",
            "forbidden_wording": "biological validation",
            "evidence_source": "Gate 13C confirmation manifest",
            "notes": "Confirmation ratio được báo cáo như computational confirmation.",
        },
        {
            "claim": "Pozo runtime",
            "status": "allowed",
            "allowed_wording": "Pozo holdout runtime passed with 12/12 successful rollouts",
            "forbidden_wording": "Pozo validated model",
            "evidence_source": "Gate 14B result summary and manifest",
            "notes": "Đây là runtime result, không phải biological validation.",
        },
        {
            "claim": "Pozo directionality",
            "status": "allowed",
            "allowed_wording": "Directional concordance was observed because distance decreased under burden 0.5",
            "forbidden_wording": "quantitative holdout validation",
            "evidence_source": "Gate 14B result summary",
            "notes": "Directionality pass không đồng nghĩa quantitative ratio match.",
        },
        {
            "claim": "Pozo quantitative ratio",
            "status": "mismatch_reported",
            "allowed_wording": "Quantitative ratio mismatch remains large",
            "forbidden_wording": "strong quantitative validation",
            "evidence_source": "Gate 14B result summary",
            "notes": "Không đặt tolerance hậu nghiệm.",
        },
        {
            "claim": "Biological validation",
            "status": "forbidden",
            "allowed_wording": "not applicable",
            "forbidden_wording": "biological Parkinson validation",
            "evidence_source": "Scientific boundary",
            "notes": "Kết quả chỉ là computational locomotion proxy.",
        },
        {
            "claim": "Gene-specific validation",
            "status": "forbidden",
            "allowed_wording": "organism-level computational proxy only",
            "forbidden_wording": "gene-specific PINK1 validation",
            "evidence_source": "Gate 14B scope and mapping flag",
            "notes": "Không có gene-specific PINK1 mapping được duyệt.",
        },
        {
            "claim": "Clinical/drug claim",
            "status": "forbidden",
            "allowed_wording": "not applicable",
            "forbidden_wording": "clinical validation; drug efficacy; therapeutic validation",
            "evidence_source": "Scientific boundary",
            "notes": "Không phải mô hình lâm sàng hay đánh giá thuốc.",
        },
    ]


def _write_claim_table() -> None:
    CLAIM_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = _claim_rows()
    with CLAIM_TABLE_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "claim",
                "status",
                "allowed_wording",
                "forbidden_wording",
                "evidence_source",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    summary: dict[str, Any], gate13c_manifest: dict[str, Any]
) -> None:
    result = summary["pozo_holdout_result"]
    confirmation_ratio = float(gate13c_manifest["confirmation_ratio"])
    report = f"""# Gate 14C - Holdout Interpretation Adjudication

## Mục tiêu

Gate 14C khóa diễn giải khoa học sau Pozo holdout. Gate này chỉ đọc các
artifact đã có và không chạy simulation mới, calibration, tuning hoặc chọn lại
parameter.

## Input

- Gate 13B: `CHEN_RATIO_CALIBRATION_PASS`.
- Gate 13C: `CHEN_CALIBRATED_CONFIRMATION_PASS`.
- Gate 14A: Pozo holdout protocol locked.
- Gate 14B: Pozo holdout runtime PASS.

## Locked parameter

- `proxy_burden_level = 0.5`.
- Không chọn lại parameter.
- Không tune trên Pozo.

## Pozo result

- Condition: `pink1`, organism-level proxy.
- Planned runs: `{result['planned_runs']}`.
- Successful runs: `{result['successful_runs']}`.
- Control distance: `{result['control_distance_mm_mean']:.5f} mm`.
- Holdout distance: `{result['holdout_distance_mm_mean']:.5f} mm`.
- Simulated distance ratio: `{result['simulated_distance_ratio']:.4f}`.
- Pozo target ratio: `{result['pozo_target_ratio']:.16f}`.
- Directionality: `PASS` (`burden 0.5` làm distance giảm so với `burden 0.0`).
- Quantitative ratio match: `NOT SUPPORTED`.
- Ratio error: `{result['ratio_error']:.12f}`.

Ratio mô phỏng `{result['simulated_distance_ratio']:.4f}` khác xa ratio Pozo
`{result['pozo_target_ratio']:.4f}`. Vì vậy không được gọi kết quả này là
quantitative holdout validation. Sai số khoảng cách tuyệt đối chỉ là
`reference-only`, không dùng để kết luận do scale/thời lượng assay và runtime
không được giả định tương đương trực tiếp.

## Adjudication

- Runtime pipeline: `PASS`.
- Directional concordance: `REPORTED`.
- Quantitative ratio mismatch: `LARGE`.
- Evidence chỉ hỗ trợ directional phenotype concordance trong một
  computational locomotion proxy ở mức organism-level.

Không được kết luận:

- biological Parkinson validation;
- gene-specific PINK1 validation;
- quantitative Pozo validation;
- clinical validation;
- drug efficacy hoặc therapeutic validation.

## Evidence boundary

Gate 13C confirmation ratio được ghi nhận là `{confirmation_ratio:.4f}`; đây là
confirmation computational của burden đã khóa, không phải biological evidence.
Gate 14C không sửa raw result Gate 14B và không thêm ngưỡng ratio hậu nghiệm.

## Final claim

Chen-calibrated organism-level computational locomotion proxy with directional
Pozo holdout concordance, but substantial quantitative ratio mismatch.

## Final status

`HOLDOUT_ADJUDICATION_COMPLETE`

`DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH`
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")


def _write_claim_document(summary: dict[str, Any], gate13c_manifest: dict[str, Any]) -> None:
    result = summary["pozo_holdout_result"]
    confirmation_ratio = float(gate13c_manifest["confirmation_ratio"])
    document = f"""# Current Claim Lock

## Phạm vi

Đây là claim lock hiện hành sau Gate 14C. Mọi báo cáo, biểu đồ và bản thảo
phải tuân theo cách diễn giải này.

## Allowed project claim

This project implements a Chen-calibrated organism-level computational
locomotion proxy for Drosophila Parkinson-like locomotor phenotypes. The locked
proxy perturbation produced directional concordance in a Pozo PINK1 holdout
check, but did not quantitatively match the Pozo disease/control distance ratio.

## Cách viết tiếng Việt được phép

Dự án xây dựng một computational locomotion proxy ở mức organism-level cho kiểu
hình vận động Parkinson-like trên Drosophila. Tham số proxy được calibration
bằng Chen 2014 và được kiểm tra holdout bằng Pozo 2022. Kết quả holdout cho
thấy đúng chiều suy giảm vận động, nhưng chưa khớp định lượng với tỉ lệ
disease/control của Pozo.

## Forbidden wording

Không dùng các cách diễn đạt sau như một kết luận tích cực:

- biological Parkinson validation;
- gene-specific validation;
- clinical validation;
- drug validation;
- quantitatively validated holdout model;
- proven Parkinson disease mechanism;
- PINK1 biological model validated.

## Evidence table

| Gate | Evidence | Interpretation |
| --- | --- | --- |
| Gate 13B | Selected burden `0.5` | Chen-only calibration objective |
| Gate 13C | Confirmation ratio `{confirmation_ratio:.4f}` | Confirmation computational của burden đã khóa |
| Gate 14B | Simulated distance ratio `{result['simulated_distance_ratio']:.4f}` | Directional concordance reported |
| Pozo 2022 | Target ratio `{result['pozo_target_ratio']:.4f}` | Holdout reference, không dùng để tune |
| Gate 14C | Ratio mismatch `{result['ratio_error']:.4f}` | Quantitative mismatch reported |

## Scientific boundary

Gate 14C không phải biological validation, không phải gene-specific PINK1 model
đã được xác nhận, không phải clinical prediction và không phải drug/therapeutic
validation.
"""
    CLAIM_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAIM_DOC_PATH.write_text(document, encoding="utf-8")


def adjudicate() -> dict[str, Any]:
    gate14b_summary, gate14b_manifest, gate14a_protocol, gate13b_config, gate13c_manifest = _verify_gate14b_inputs()
    source_paths = [
        GATE_14B_SUMMARY,
        GATE_14B_MANIFEST,
        GATE_14A_PROTOCOL,
        GATE_13B_CONFIG,
        GATE_13C_MANIFEST,
    ]

    control_distance = float(gate14b_summary["mean_distance_control"])
    holdout_distance = float(gate14b_summary["mean_distance_holdout"])
    simulated_ratio = float(gate14b_summary["simulated_distance_ratio"])
    pozo_ratio = float(gate14b_summary["pozo_target_ratio"])
    ratio_error = abs(simulated_ratio - pozo_ratio)
    directionality_pass = bool(gate14b_summary["directionality_pass"])
    _require(directionality_pass, "Gate 14B directionality must be true for this adjudication")
    _require(holdout_distance < control_distance, "Holdout distance is not below control distance")

    reported_ratio_error = gate14b_summary.get("ratio_error")
    _require(
        reported_ratio_error is not None
        and math.isclose(float(reported_ratio_error), ratio_error, abs_tol=1e-12),
        "Gate 14B ratio_error does not match the exact source values",
    )

    pozo_result = {
        "condition_id": gate14b_summary["condition_id"],
        "scope": gate14b_summary["proxy_scope"],
        "planned_runs": gate14b_summary["planned_runs"],
        "successful_runs": gate14b_summary["successful_runs"],
        "control_distance_mm_mean": control_distance,
        "holdout_distance_mm_mean": holdout_distance,
        "simulated_distance_ratio": simulated_ratio,
        "pozo_target_ratio": pozo_ratio,
        "ratio_error": ratio_error,
        "directionality_pass": directionality_pass,
        "quantitative_ratio_match": False,
    }
    summary = {
        "schema_version": "gate-14c-holdout-adjudication-summary-v1",
        "status": "HOLDOUT_ADJUDICATION_COMPLETE",
        "final_adjudication_status": FINAL_STATUS,
        "pipeline_status": {
            "chen_ratio_calibration": "CHEN_RATIO_CALIBRATION_PASS",
            "chen_confirmation": "CHEN_CALIBRATED_CONFIRMATION_PASS",
            "pozo_protocol": "READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT",
            "pozo_runtime": "POZO_HOLDOUT_RUNTIME_PASS",
        },
        "locked_parameter": {
            "proxy_burden_level": 0.5,
            "no_parameter_reselection": True,
            "no_pozo_tuning": True,
        },
        "pozo_holdout_result": pozo_result,
        "claim_lock": {
            "allowed_primary_claim": "Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout concordance and quantitative ratio mismatch.",
            "biological_validation": False,
            "gene_specific_validation": False,
            "clinical_validation": False,
            "drug_validation": False,
            "quantitative_pozo_validation": False,
            "disease_mechanism_validation": False,
        },
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_parameter_reselection": True,
        "no_pozo_tuning": True,
        "no_gate14b_raw_result_modification": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "notes": [
            "Runtime PASS means the holdout pipeline executed successfully.",
            "Directionality PASS means distance decreased under the locked burden.",
            "The simulated ratio remains far from the Pozo target ratio.",
            "This supports directional phenotype concordance only.",
        ],
    }
    _write_json(SUMMARY_PATH, summary)
    _write_claim_table()
    _write_report(summary, gate13c_manifest)
    _write_claim_document(summary, gate13c_manifest)

    manifest = {
        "schema_version": "gate-14c-holdout-adjudication-manifest-v1",
        "status": "HOLDOUT_ADJUDICATION_COMPLETE",
        "final_adjudication_status": FINAL_STATUS,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "source_files": [_relative(path) for path in source_paths],
        "source_file_records": [
            {"path": _relative(path), "sha256": _sha256(path)}
            for path in source_paths
        ],
        "summary_json_sha256": _sha256(SUMMARY_PATH),
        "claim_lock_table_sha256": _sha256(CLAIM_TABLE_PATH),
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_parameter_reselection": True,
        "no_pozo_tuning": True,
        "no_gate14b_raw_result_modification": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "large_artifacts_committed": False,
    }
    _write_json(MANIFEST_PATH, manifest)
    return summary


def main() -> int:
    try:
        summary = adjudicate()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        print(f"Gate 14C adjudication failed: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {summary['status']}")
    print(f"Final status: {summary['final_adjudication_status']}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
