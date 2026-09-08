from scripts.audit_holdout_firewall import audit


def test_gate24_holdout_is_sealed() -> None:
    result = audit()
    assert result["status"] == "SEALED"
    assert result["raw_data_opened"] is False
    assert result["numeric_values_imported"] is False
    assert result["used_for_parameter_selection"] is False
    assert result["used_for_threshold_selection"] is False
    assert result["used_for_seed_selection"] is False
    assert result["used_for_model_selection"] is False
    assert result["no_holdout_tuning"] is True
