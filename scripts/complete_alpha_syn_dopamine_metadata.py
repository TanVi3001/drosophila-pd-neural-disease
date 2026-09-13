#!/usr/bin/env python3
"""Complete source-audited metadata without authorizing scientific execution.

The script enriches the already prepared alpha-synuclein/dopamine registry
with values that are explicitly supported by the local review artifacts or
primary full text. It never imputes a statistic, changes a study allocation,
fits a parameter, or launches a simulator.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from prepare_alpha_syn_dopamine_direction import FIELDNAMES, METADATA_OVERRIDES


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
REGISTRY = PREP / "literature_endpoint_registry_v2.csv"
SPLIT = PREP / "alpha_syn_dopamine_study_split_manifest_v1.json"
DIRECTION_SIGNOFF = PREP / "alpha_syn_dopamine_review_signoff.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalize_registry(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for raw in rows:
        row = {field: raw.get(field, "") for field in FIELDNAMES}
        row["center_value"] = row["center_value"] or "NOT_REPORTED"
        row["experimental_unit"] = row["experimental_unit"] or row.get("sample_unit", "NOT_REPORTED")
        row["assay_transfer_basis"] = row["assay_transfer_basis"] or "PENDING_SOURCE_AND_REVIEW_ADJUDICATION"
        override = METADATA_OVERRIDES.get(row["endpoint_id"], {})
        row.update(override)
        if override:
            row["reviewer_1"] = "PENDING_RECONFIRMATION"
            row["reviewer_2_recorded"] = "PENDING_RECONFIRMATION"
            row["review_date"] = "NOT_RECORDED_FOR_UPDATED_METADATA"
        normalized.append(row)
    return normalized


def write_updated_review_packet(rows: list[dict[str, str]]) -> None:
    pending = [row for row in rows if row["approval_status"] == "PENDING_HUMAN_REVIEW"]
    missing_center = [row["endpoint_id"] for row in rows if row["center_value"] in {"", "NOT_REPORTED"}]
    missing_spread = [row["endpoint_id"] for row in rows if row["spread_value"] in {"", "NOT_REPORTED"}]
    missing_duration = [row["endpoint_id"] for row in rows if row["duration_s"] in {"", "NOT_REPORTED"}]
    text = f"""# Alpha-synuclein/dopamine updated metadata review packet

Status: `READY_FOR_DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW`
Review date prepared: {date.today().isoformat()}

## What changed

The endpoint registry was refreshed from the primary-source full text and
existing project review artifacts. The new explicit fields are `center_value`,
`spread_type`, `spread_value`, `unit`, `duration_s`, `assay_transfer`, and
`experimental_unit`. Values that remain unavailable are recorded as
`NOT_REPORTED`; no bar height or sample-size range was converted into a false
numeric observation.

## Current source-audit counts

- Registry rows: `{len(rows)}`
- Rows still pending human review: `{len(pending)}`
- Missing numeric center: `{len(missing_center)}`
- Missing numeric spread: `{len(missing_spread)}`
- Missing assay duration: `{len(missing_duration)}`

## Required reviewer checks

- [ ] Every newly filled center and spread matches the cited primary source or
  a clearly labelled project digitization artifact.
- [ ] `median` is not relabelled as `mean`; IQR/min-max is not relabelled as
  SD/SE; approximate digitization remains labelled approximate.
- [ ] Experimental unit is the unit used by the study analysis, not the number
  of flies multiplied by the number of vials.
- [ ] Distance, activity time, DAM activity, and climbing remain separate from
  planar walking speed.
- [ ] Assay transfer is adjudicated per endpoint; unresolved transfer remains
  `pending` and cannot open a fitting gate.
- [ ] The preregistration scope, baselines, split, estimand, and claim boundary
  are acceptable before any model fitting.
- [ ] This review is not GPU execution authorization.

## Explicit attestations

### Reviewer 1 — Lê Tấn Vĩ

- Registry reviewed: ______________________________
- Preregistration v1 reviewed: _____________________
- Confirmation: ___________________________________
- Date: __________________

### Reviewer 2 — Tô Đặng Minh Tuấn

- Registry reviewed: ______________________________
- Preregistration v1 reviewed: _____________________
- Confirmation: ___________________________________
- Date: __________________

Until both attestations are recorded, the separate execution authorization
must remain `authorized=false` and no scientific GPU run may start.
"""
    (PREP / "alpha_syn_dopamine_updated_metadata_review_packet.md").write_text(
        text, encoding="utf-8"
    )


def main() -> int:
    rows = normalize_registry(read_csv(REGISTRY))
    write_csv(REGISTRY, rows)
    registry_hash = sha256(REGISTRY)

    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    split["status"] = "ALLOCATION_LOCKED_PENDING_UPDATED_METADATA_REVIEW"
    split["preparation_only"] = True
    split["gpu_execution_authorized"] = False
    split["parameter_fitting_authorized"] = False
    split["allocation_lock"] = {
        **split.get("allocation_lock", {}),
        "locked_at": split.get("allocation_lock", {}).get("locked_at", date.today().isoformat()),
        "basis": "PRIOR_DUAL_HUMAN_DIRECTION_REVIEW_PASS_PLUS_SOURCE_METADATA_REFRESH",
        "registry_sha256": registry_hash,
        "fitting_authorized": False,
        "gpu_execution_authorized": False,
    }
    for allocation in split.get("planned_allocations", []):
        allocation["allocation_status"] = "LOCKED_PENDING_UPDATED_METADATA_REVIEW"
        allocation["review_status"] = "PENDING_UPDATED_METADATA_REVIEW"
        allocation["fit_allowed_now"] = False
    split["metadata_review"] = {
        "status": "SOURCE_AUDITED_PENDING_DUAL_HUMAN_RECONFIRMATION",
        "registry_sha256": registry_hash,
        "review_packet": "alpha_syn_dopamine_updated_metadata_review_packet.md",
        "unresolved_fields_are_preserved": True,
    }
    split["required_before_fitting"] = [
        "dual human review of the updated registry and preregistration",
        "numeric metadata and assay transfer only where source-supported",
        "complete alpha-synuclein/dopamine model and runner audit",
        "separate explicit execution authorization",
    ]
    write_json(SPLIT, split)

    direction = json.loads(DIRECTION_SIGNOFF.read_text(encoding="utf-8"))
    direction["metadata_refresh_status"] = "PENDING_DUAL_HUMAN_RECONFIRMATION"
    direction["updated_registry_sha256"] = registry_hash
    direction["next_action"] = "Both reviewers re-confirm the updated registry and preregistration before fitting or GPU authorization."
    direction["gpu_execution_authorized"] = False
    direction["parameter_fitting_authorized"] = False
    write_json(DIRECTION_SIGNOFF, direction)

    updated_signoff = {
        "schema_version": "alpha-syn-dopamine-updated-registry-prereg-review-v1",
        "status": "PENDING_DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW",
        "scope": "updated endpoint registry, final preregistration v1, and claim boundary",
        "registry": REGISTRY.name,
        "registry_sha256": registry_hash,
        "gpu_execution_authorized": False,
        "parameter_fitting_authorized": False,
        "holdout_opened": False,
        "reviewers": [
            {"name": "Lê Tấn Vĩ", "role": "reviewer_1", "status": "PENDING_HUMAN_CONFIRMATION", "attestation": None},
            {"name": "Tô Đặng Minh Tuấn", "role": "reviewer_2", "status": "PENDING_HUMAN_CONFIRMATION", "attestation": None},
        ],
        "required_materials": [
            "literature_endpoint_registry_v2.csv",
            "alpha_syn_dopamine_study_split_manifest_v1.json",
            "alpha_syn_dopamine_preregistration_v1.md",
            "alpha_syn_dopamine_preregistration_v1.json",
            "alpha_syn_dopamine_updated_metadata_review_packet.md",
        ],
        "next_action": "Record two direct reviewer attestations; this signoff is not execution authorization.",
    }
    write_json(PREP / "alpha_syn_dopamine_updated_registry_prereg_review_signoff_v1.json", updated_signoff)
    write_updated_review_packet(rows)

    manifest = {
        "schema_version": "alpha-syn-dopamine-source-metadata-refresh-v1",
        "status": "SOURCE_AUDITED_PENDING_DUAL_HUMAN_RECONFIRMATION",
        "created_at": date.today().isoformat(),
        "registry": REGISTRY.name,
        "registry_sha256": registry_hash,
        "rows": len(rows),
        "center_filled": sum(row["center_value"] not in {"", "NOT_REPORTED"} for row in rows),
        "spread_filled": sum(row["spread_value"] not in {"", "NOT_REPORTED"} for row in rows),
        "duration_filled": sum(row["duration_s"] not in {"", "NOT_REPORTED"} for row in rows),
        "experimental_unit_filled": sum(row["experimental_unit"] not in {"", "NOT_REPORTED"} for row in rows),
        "no_imputation": True,
        "no_gpu_execution": True,
        "no_fitting": True,
        "no_holdout_opened": True,
    }
    write_json(PREP / "alpha_syn_dopamine_source_metadata_refresh_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
