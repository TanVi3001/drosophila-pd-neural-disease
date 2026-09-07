from pathlib import Path

from drosophila_pd_neural.riemensperger2011.protocol import read_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_replication_configs_use_same_seed_policy_and_no_disease_in_healthy() -> None:
    healthy = read_yaml(ROOT / "configs/replications/riemensperger_2011_healthy.yaml")
    disease = read_yaml(ROOT / "configs/replications/riemensperger_2011_dopamine_deficiency.yaml")
    assert healthy["seed_policy"]["seeds"] == [0, 1, 2, 3, 4]
    assert healthy["disease_layer"] is False
    assert disease["seed_policy"]["seeds"] == healthy["seed_policy"]["seeds"]
    assert disease["parameter_policy"]["calibration_forbidden"] is True
    assert disease["parameter_policy"]["holdout_forbidden"] is True
