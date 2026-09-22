from pathlib import Path

from scripts.run_riemensperger2011_replication_pipeline import _write_final_report


ROOT = Path(__file__).resolve().parents[1]


def test_pending_claim_lock_does_not_claim_biological_validation(tmp_path: Path) -> None:
    report_path = tmp_path / "final_replication_report.md"
    _write_final_report(
        {"21A": "RIEMENSPERGER_2011_EVIDENCE_LOCKED", "21D": "WAITING_DOPAMINE_MAPPING_REVIEW"},
        report_path=report_path,
        status_path=tmp_path / "pipeline_status.json",
    )
    report = report_path.read_text(encoding="utf-8")
    assert "no biological validation claim is made" in report
    assert "gene-specific validation" in report
    assert "drug validation" in report
