from scripts.decide_gene_specific_validation import decide


def test_decision_engine_preserves_failed_validation() -> None:
    result = decide({"criteria": {}, "biological_data_available": False})
    assert result["status"] == "GENE_SPECIFIC_VALIDATION_NOT_SUPPORTED"
    assert result["parkinson_like_biological_support"] == "PARKINSON_LIKE_BIOLOGICAL_SUPPORT_INCOMPLETE"
    assert result["model_result_does_not_promote_itself"] is True
