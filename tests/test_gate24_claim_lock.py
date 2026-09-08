import json

from scripts.audit_gate24_prediction_readiness import audit


def test_gate24_never_issues_biological_validation_claim() -> None:
    result = audit()
    assert result["data_fabricated"] is False
    assert result["gpu_executed"] is False
    assert result["simulation_executed"] is False
    assert "no biological validation claim" in result["allowed_claim"].lower()
    assert "biological validation supported" not in result["allowed_claim"].lower()
    assert "BIOLOGICALLY_VALIDATED" in result["forbidden_claims"]
    assert "PARKINSON_VALIDATED" in result["forbidden_claims"]
