from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_validation_target_locks_safe_scope_and_excludes_overclaims() -> None:
    target = yaml.safe_load((ROOT / "research/validation/claim_policy/validation_target.yaml").read_text(encoding="utf-8"))
    assert target["status"] == "VALIDATION_TARGET_LOCKED"
    assert target["primary_gene"] == "parkin"
    assert "Validated Parkinson disease" in target["excluded_claims"]
    assert target["track_a_boundary"]
