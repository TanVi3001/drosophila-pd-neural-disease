import json
from pathlib import Path

from scripts.analyze_riemensperger2011_four_group import run
from scripts.lock_riemensperger2011_evidence import lock_evidence
from drosophila_pd_neural.riemensperger2011.protocol import write_json


ROOT = Path(__file__).resolve().parents[1]


def test_four_group_analysis_uses_ratio_and_never_fits_holdout(tmp_path: Path) -> None:
    evidence_output = tmp_path / "evidence"
    lock_evidence(
        lock_path=ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv",
        contract_path=ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml",
        policy_path=ROOT / "research/replications/riemensperger_2011/protocols/control_policy.md",
        output=evidence_output,
    )
    healthy = tmp_path / "healthy.json"
    disease = tmp_path / "disease.json"
    write_json(healthy, {"status": "HEALTHY_VIRTUAL_REPLICATION_PASS", "median_planar_speed_mm_s": {"median": 2.0, "sample_sd": 0.1, "n_seeds": 5}})
    write_json(disease, {"status": "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS", "median_planar_speed_mm_s": {"median": 1.0, "sample_sd": 0.1, "n_seeds": 5}})
    output = tmp_path / "analysis"
    status = run(
        evidence_lock=ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv",
        contract_path=ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml",
        analysis_config=ROOT / "configs/replications/riemensperger_2011_analysis.yaml",
        healthy_path=healthy,
        disease_path=disease,
        output=output,
    )
    assert status == "FOUR_GROUP_ANALYSIS_COMPLETE"
    summary = json.loads((output / "results/four_group_summary.json").read_text(encoding="utf-8"))
    assert summary["comparison"]["real_effect_ratio"] == 7.8 / 10.8
    assert summary["comparison"]["virtual_effect_ratio"] == 0.5
    assert summary["comparison"]["quantitative_match"] == "NOT_ASSESSED_NO_PREREGISTERED_THRESHOLD"
    assert summary["calibration_run"] is False
    assert summary["holdout_validation_run"] is False
