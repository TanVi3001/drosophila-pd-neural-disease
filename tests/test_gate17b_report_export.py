from __future__ import annotations

import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "experiments/gate_17b_report_export"
RESULTS = EXPORT_ROOT / "results"
MANIFEST = EXPORT_ROOT / "manifests/report_export_manifest.json"
SUMMARY = RESULTS / "report_export_summary.json"
DOCX = RESULTS / "final_vietnamese_report.docx"
PDF = RESULTS / "final_vietnamese_report.pdf"


def test_gate17b_export_artifacts_exist() -> None:
    for path in (
        ROOT / "docs/report/export_readme.md",
        ROOT / "scripts/export_final_report_package.py",
        ROOT / "docs/report/final_vietnamese_report.md",
        DOCX,
        PDF,
        SUMMARY,
        MANIFEST,
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 0, path


def test_gate17b_summary_is_claim_safe() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] in {"REPORT_EXPORT_READY", "REPORT_EXPORT_PARTIAL"}
    assert summary["claim_lock_active"] is True
    assert summary["no_new_simulation_run"] is True
    assert summary["no_calibration_run"] is True
    assert summary["no_tuning_run"] is True
    assert summary["no_raw_metric_modification"] is True
    assert "organism-level computational locomotion proxy" in summary["final_claim"]
    assert "directional Pozo holdout concordance" in summary["final_claim"]
    assert "quantitative ratio mismatch" in summary["final_claim"]
    assert summary["boundaries"] == {
        "biological_validation": False,
        "gene_specific_validation": False,
        "clinical_validation": False,
        "drug_validation": False,
        "therapeutic_validation": False,
    }


def test_gate17b_manifest_records_export_provenance() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] in {"REPORT_EXPORT_READY", "REPORT_EXPORT_PARTIAL"}
    assert manifest["claim_lock_active"] is True
    assert manifest["large_artifacts_committed"] is False
    assert manifest["visual_qa_status"]
    assert set(manifest["sha256"]) == {
        "docs/report/final_vietnamese_report.md",
        "docs/report/export_readme.md",
        "experiments/gate_17b_report_export/results/final_vietnamese_report.docx",
        "experiments/gate_17b_report_export/results/final_vietnamese_report.pdf",
        "experiments/gate_17b_report_export/results/report_export_summary.json",
    }


def test_gate17b_docx_contains_report_text() -> None:
    with zipfile.ZipFile(DOCX) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    for phrase in (
        "Báo cáo tổng kết dự án",
        "0.6701030927835051",
        "0.6142225784",
        "0.9470",
        "0.1920",
        "directional",
    ):
        assert phrase in document_xml


def test_gate17b_pdf_contains_report_text() -> None:
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(PDF)).pages)
    for phrase in (
        "Báo cáo tổng kết dự án",
        "0.6701030927835051",
        "0.6142225784",
        "0.9470",
        "0.1920",
    ):
        assert phrase in text


def test_gate17b_no_positive_overclaim_in_export_readme() -> None:
    text = (ROOT / "docs/report/export_readme.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "biologically validated",
        "clinically validated",
        "drug efficacy",
        "therapeutic efficacy",
        "proves parkinson",
        "gene-specific validation achieved",
        "quantitatively validated",
    ):
        assert phrase not in text
