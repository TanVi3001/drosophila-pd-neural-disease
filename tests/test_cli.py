from pathlib import Path

from scripts.apply_neural_condition import main


def test_cli_waits_without_declared_burden_curve(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "condition"
    code = main(
        [
            "--config",
            str(root / "configs" / "conditions" / "alpha_synuclein.template.yaml"),
            "--age-days",
            "20",
            "--output",
            str(output),
        ]
    )
    assert code == 0
    assert '"status": "WAITING_TARGET_DATA"' in (output / "status.json").read_text(encoding="utf-8")
