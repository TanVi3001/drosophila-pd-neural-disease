import csv
import json
from pathlib import Path

from scripts.fetch_brain_source import SOURCE_FILES


ROOT = Path(__file__).resolve().parents[1]


def test_source_catalog_matches_pinned_fetch_contract() -> None:
    catalog = json.loads((ROOT / "data/source_catalog.json").read_text(encoding="utf-8"))
    report = catalog["source_report"]
    assert report["status"] == "AUDITED_NOT_AUTHORITATIVE"
    assert len(report["sha256"]) == 64

    files = catalog["verified_external_source"]["files"]
    assert files
    for record in files:
        pinned = SOURCE_FILES[record["path"]]
        assert record["size"] == pinned["size"]
        assert record["sha256"] == pinned["sha256"]


def test_artifact_audit_does_not_promote_missing_files() -> None:
    with (ROOT / "research/dataset_intake/artifact_audit.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    for row in rows:
        if row["integrity_status"].startswith("MISSING"):
            assert row["integration_status"] == "NOT_INTEGRATED"


def test_literature_intake_has_no_approved_numeric_targets() -> None:
    with (ROOT / "research/dataset_intake/literature_source_review.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert not any(row["review_status"] == "approved" for row in rows)
    rejected = {row["paper_id"]: row for row in rows if row["review_status"].startswith("REJECTED")}
    assert rejected["Liessem_2026"]["doi"] == "10.1016/j.cub.2025.12.015"
