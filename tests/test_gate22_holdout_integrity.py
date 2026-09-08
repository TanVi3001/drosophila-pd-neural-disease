from scripts.import_gene_specific_biological_validation import validate_rows


def test_biological_import_rejects_synthetic_and_frame_pseudoreplication() -> None:
    row = {"source_type": "SYNTHETIC", "sample_id": "frame", "biological_replicate": "frame", "used_for_calibration": "true", "used_for_validation": "false"}
    errors = validate_rows([row])
    assert any("rejected_source_type" in error for error in errors)
    assert any("frame_cannot_be_biological_replicate" in error for error in errors)
    assert any("used_for_calibration_must_be_false" in error for error in errors)
