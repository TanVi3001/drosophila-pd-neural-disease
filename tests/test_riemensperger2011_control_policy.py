from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dthg_ple_is_primary_control_and_wt_is_secondary() -> None:
    policy = (ROOT / "research/replications/riemensperger_2011/protocols/control_policy.md").read_text(encoding="utf-8")
    assert "DTHg; ple` là **primary real control**" in policy
    assert "`WT` (Canton S) chỉ là **secondary reference**" in policy
    assert "median -> mean" not in policy
