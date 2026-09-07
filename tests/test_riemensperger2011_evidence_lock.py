from pathlib import Path

from scripts.lock_riemensperger2011_evidence import lock_evidence
from drosophila_pd_neural.riemensperger2011.protocol import read_json


ROOT = Path(__file__).resolve().parents[1]


def test_evidence_lock_preserves_primary_control_and_disease(tmp_path: Path) -> None:
    status = lock_evidence(
        lock_path=ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv",
        contract_path=ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml",
        policy_path=ROOT / "research/replications/riemensperger_2011/protocols/control_policy.md",
        output=tmp_path,
    )
    assert status == "RIEMENSPERGER_2011_EVIDENCE_LOCKED"
    summary = read_json(tmp_path / "results/evidence_lock_summary.json")
    assert summary["primary_real_control"] == "DTHg; ple"
    assert summary["real_disease"] == "DTHgFS±; ple"
    assert summary["real_speed_ratio"] == 7.8 / 10.8
    assert summary["data_fabricated"] is False
