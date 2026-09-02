from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_gate15a_documentation_files_exist() -> None:
    for relative in (
        "README.md",
        "docs/project_summary.md",
        "docs/limitations.md",
        "docs/results_timeline.md",
        "docs/claims/public_abstract.md",
        "docs/claims/claim_safe_wording_guide.md",
    ):
        assert (ROOT / relative).is_file(), relative


def test_readme_records_locked_gate_results() -> None:
    readme = _read("README.md")
    for phrase in (
        "CHEN_RATIO_CALIBRATION_PASS",
        "CHEN_CALIBRATED_CONFIRMATION_PASS",
        "POZO_HOLDOUT_RUNTIME_PASS",
        "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH",
        "0.9470",
        "0.1920",
    ):
        assert phrase in readme
    assert "0.5 s" in readme or "0.5 giây" in readme


def test_public_abstract_has_scientific_boundary() -> None:
    abstract = _read("docs/claims/public_abstract.md").lower()
    assert "not biological" in abstract
    assert "not gene-specific" in abstract


def test_claim_guide_contains_allowed_and_forbidden_sections() -> None:
    guide = _read("docs/claims/claim_safe_wording_guide.md").lower()
    assert "## allowed wording" in guide
    assert "## forbidden wording" in guide
    assert "computational locomotion proxy" in guide
    assert "biological parkinson validation" in guide


def test_public_documents_do_not_make_positive_overclaims() -> None:
    documents = "\n".join(
        _read(relative)
        for relative in (
            "README.md",
            "docs/project_summary.md",
            "docs/claims/public_abstract.md",
        )
    ).lower()
    positive_overclaims = (
        "biologically validated",
        "clinically validated",
        "drug efficacy",
        "therapeutic efficacy",
        "proves parkinson",
        "gene-specific validation achieved",
        "quantitatively validated",
    )
    for phrase in positive_overclaims:
        assert phrase not in documents
