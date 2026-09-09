from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.run_presentation_demo as demo


def test_default_preflight_does_not_simulate(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = {"status": "DEMO_PREFLIGHT_PASS", "blockers": []}
    monkeypatch.setattr(demo, "preflight", lambda: result)
    monkeypatch.setattr(demo, "execute", lambda: pytest.fail("default invocation executed simulation"))
    assert demo.main([]) == 0
    assert "DEMO_PREFLIGHT_PASS" in capsys.readouterr().out


def test_scientific_evidence_paths_are_rejected() -> None:
    with pytest.raises(demo.DemoError, match="protected"):
        demo.output_isolation_check(demo.ROOT / "experiments/gate_24e_blinded_parkin_prediction/demo")


def test_wrong_runtime_sha_is_rejected() -> None:
    with pytest.raises(demo.DemoError, match="Runtime commit mismatch"):
        demo.validate_runtime_commit("0" * 40)


def test_wrong_checkpoint_sha_is_rejected(tmp_path: Path) -> None:
    checkpoint = tmp_path / "plastic_weights.pt"
    checkpoint.write_bytes(b"not-a-frozen-checkpoint")
    with pytest.raises(demo.DemoError, match="SHA256 mismatch"):
        demo.validate_checkpoint(checkpoint, "0" * 64, "Parkin p=1.00")


def test_steps_above_safe_maximum_are_rejected() -> None:
    with pytest.raises(demo.DemoError, match="exactly 12000"):
        demo.validate_demo_parameters(steps=12001)


def test_only_seed_zero_is_allowed() -> None:
    with pytest.raises(demo.DemoError, match="Only seed 0"):
        demo.validate_demo_parameters(seed=1)


def test_only_healthy_and_p100_presets_exist(tmp_path: Path) -> None:
    healthy = demo.build_command("healthy", tmp_path / "healthy")
    parkin = demo.build_command("parkin_p100", tmp_path / "parkin", Path("p100.pt"))
    assert "--prepared-checkpoint" not in healthy
    assert "--prepared-checkpoint" in parkin
    assert "--compare-to" not in healthy + parkin
    with pytest.raises(demo.DemoError, match="Unsupported demo condition"):
        demo.build_command("parkin_p050", tmp_path / "other", Path("p050.pt"))


def test_manifest_declares_demo_only_and_no_scientific_evidence() -> None:
    manifest = demo.build_manifest(
        {
            "canonical_remote_main_commit": "main",
            "demo_source_commit": "source",
            "demo_source_is_ancestor_of_canonical_main": True,
            "gate25_r2_freeze_sha256": demo.CURRENT_R2_SHA256,
            "previous_gate25_r2_freeze_sha256": demo.PREVIOUS_R2_SHA256,
            "gate24e_scientific_result": demo.GATE24E_RESULT,
            "gate24e_cross_assay_decision": demo.GATE24E_CROSS_ASSAY,
        },
        {"status": "PASS"},
        {"status": "PASS"},
        {"preflight": {"available": False}},
    )
    assert manifest["scientific_evidence"] is False
    assert manifest["demo_only"] is True
    assert manifest["scientific_batch_rerun"] is False
    assert manifest["validation_analysis"] is False


def test_execute_one_runs_once_without_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "healthy"
    (output).mkdir()
    (output / "status.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    (output / "flygym_rollout.mp4").write_bytes(b"demo")
    calls: list[list[str]] = []
    monkeypatch.setattr(demo, "_runtime_telemetry", lambda: {"available": False})
    monkeypatch.setattr(demo, "build_command", lambda *_args, **_kwargs: ["runner"])
    monkeypatch.setattr(demo.subprocess, "run", lambda command, **_kwargs: calls.append(command) or type("R", (), {"returncode": 0})())
    result = demo._execute_one("healthy", output, None)
    assert result["status"] == "PASS"
    assert calls == [["runner"]]
