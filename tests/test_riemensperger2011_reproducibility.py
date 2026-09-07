import hashlib
from pathlib import Path

from drosophila_pd_neural.riemensperger2011.protocol import build_manifest, sha256_file


def test_manifest_records_config_and_input_checksums(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    data = tmp_path / "input.csv"
    config.write_text("seed: 0\n", encoding="utf-8")
    data.write_text("metric,value\nspeed,1.0\n", encoding="utf-8")
    manifest = build_manifest(status="TEST", config_paths=[config], input_paths=[data], extra={"simulation_run": False})
    assert manifest["config_inputs"][0]["sha256"] == sha256_file(config)
    assert manifest["data_inputs"][0]["sha256"] == sha256_file(data)
    assert manifest["simulation_run"] is False
    assert manifest["data_fabricated"] is False


def test_gate_checksum_manifests_match_small_committed_artifacts() -> None:
    gates = (
        "gate_21a_riemensperger_evidence_lock",
        "gate_21b_riemensperger_healthy",
        "gate_21c_riemensperger_healthy_comparability",
        "gate_21d_riemensperger_dopamine_mapping",
        "gate_21e_riemensperger_disease",
        "gate_21f_four_group_analysis",
        "gate_21g_riemensperger_robustness",
    )
    for gate_name in gates:
        gate = Path("experiments") / gate_name
        manifest = gate / "manifests/checksums.sha256"
        assert manifest.is_file(), gate_name
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            path = gate / relative
            assert path.is_file(), relative
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
