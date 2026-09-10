import hashlib
import subprocess
from pathlib import Path

from drosophila_pd_neural.riemensperger2011.protocol import build_manifest, sha256_file


LEGACY_CHECKSUM_EXCEPTIONS = {
    (
        "gate_21c_riemensperger_healthy_comparability",
        "results/healthy_comparability.csv",
    ): {
        "gate": "gate_21c_riemensperger_healthy_comparability",
        "path": "results/healthy_comparability.csv",
        "reason": "The legacy Gate21C manifest points to a generated CSV absent from the public main snapshot.",
        "historical_provenance_basis": (
            "The artifact is present as Git blob 410b0dfbedb2cd7ea2713199fd6d6321c79421e2 "
            "on research/gate27-riemensperger-robustness at commit "
            "267323e121d0f1bc069dd176e869252af3a81dc4, but is not in "
            "origin/main snapshot 353ba33eb635138dcee5a65819e8f723d7448efc."
        ),
    }
}


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
        # Every checksum manifest in this legacy family stores gate-relative
        # paths; resolve them below as ROOT/experiments/<gate>/relative.
        gate = Path("experiments") / gate_name
        manifest = gate / "manifests/checksums.sha256"
        assert manifest.is_file(), gate_name
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            path = gate / relative
            # Historical manifests may contain a platform-specific CRLF
            # serialization; compare it with the canonical Git blob without
            # changing the immutable evidence files.
            result = subprocess.run(
                ["git", "cat-file", "blob", f"HEAD:{path.as_posix()}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                exception = LEGACY_CHECKSUM_EXCEPTIONS.get((gate_name, relative))
                assert exception is not None, (
                    "missing committed checksum artifact without an explicit "
                    f"exception: {gate_name}/{relative}"
                )
                assert exception["gate"] == gate_name
                assert exception["path"] == relative
                assert exception["reason"]
                assert exception["historical_provenance_basis"]
                assert not path.exists(), relative
                continue
            blob = result.stdout
            canonical_sha = hashlib.sha256(blob).hexdigest()
            crlf_sha = hashlib.sha256(blob.replace(b"\n", b"\r\n")).hexdigest()
            assert digest in {canonical_sha, crlf_sha}, relative


def test_missing_legacy_artifact_policy_has_no_implicit_fallback() -> None:
    assert ("unknown_gate", "missing/artifact.json") not in LEGACY_CHECKSUM_EXCEPTIONS
    exception = LEGACY_CHECKSUM_EXCEPTIONS[
        (
            "gate_21c_riemensperger_healthy_comparability",
            "results/healthy_comparability.csv",
        )
    ]
    assert exception["reason"]
    assert exception["historical_provenance_basis"]
