from pathlib import Path

from drosophila_pd_neural.riemensperger2011.protocol import read_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_endpoint_contract_keeps_median_and_forbids_distance_conversion() -> None:
    document = read_yaml(ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml")
    primary = document["primary_endpoint"]
    assert primary["paper_metric"] == "median_planar_speed_mm_s"
    assert primary["statistic"] == "median"
    assert "distance_to_speed" in document["forbidden_conversions"]
    assert document["secondary_endpoints"][0]["comparability"] == "NOT_COMPARABLE_WITH_CURRENT_VIRTUAL_DURATION"
