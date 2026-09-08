from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_report_does_not_claim_biological_parkinson_validation() -> None:
    report = (ROOT / "docs/validation/gene_specific_biological_validation_report.md").read_text(encoding="utf-8")
    assert "does not support a gene-specific or biological Parkinson validation claim" in report
    assert "No biological measurements were generated" in report
