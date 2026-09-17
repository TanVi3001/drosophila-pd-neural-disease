"""Read-only contract inspection for the canonical FlyGym platform.

The neural repository is an additive extension. This module records the
platform capabilities it needs without importing FlyGym or changing the
platform worktree. The current platform contract is based on its public
``Perturbation`` protocol and canonical healthy-baseline experiment runner.
"""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from pathlib import Path
import tomllib
from typing import Any


PLATFORM_REQUIRED_FILES = (
    "pyproject.toml",
    "src/drosophila_pd/__init__.py",
    "src/drosophila_pd/perturbations/base.py",
    "src/drosophila_pd/experiments/healthy_baseline.py",
    "scripts/run_healthy_baseline.py",
    "scripts/run_brain_driven_experiment.py",
)


def default_platform_root() -> Path:
    """Return the sibling platform path used by the documented layout."""

    return Path(__file__).resolve().parents[3] / "drosophila-pd-flygym"


@dataclass(frozen=True)
class PlatformContract:
    """Machine-readable result of a platform source inspection."""

    root: str
    status: str
    package_name: str | None
    package_version: str | None
    python_requirement: str | None
    git_commit: str | None
    worktree_dirty: bool | None
    capabilities: tuple[str, ...]
    missing_files: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """Whether all source-level integration requirements are present."""

        return self.status == "READY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "status": self.status,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "python_requirement": self.python_requirement,
            "git_commit": self.git_commit,
            "worktree_dirty": self.worktree_dirty,
            "capabilities": list(self.capabilities),
            "missing_files": list(self.missing_files),
            "blockers": list(self.blockers),
            "scientific_scope": (
                "Source-level platform compatibility inspection only; no simulation "
                "was run and no biological claim is made."
            ),
        }


def inspect_platform(root: str | Path) -> PlatformContract:
    """Inspect a platform checkout without importing or mutating it."""

    platform_root = Path(root).expanduser().resolve()
    missing = tuple(
        relative
        for relative in PLATFORM_REQUIRED_FILES
        if not (platform_root / relative).is_file()
    )
    blockers: list[str] = []
    package_name: str | None = None
    package_version: str | None = None
    python_requirement: str | None = None

    pyproject = platform_root / "pyproject.toml"
    if pyproject.is_file():
        try:
            document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = document.get("project", {})
            package_name = project.get("name")
            package_version = project.get("version")
            python_requirement = project.get("requires-python")
            if package_name != "drosophila-pd-flygym":
                blockers.append(f"platform_package_name={package_name!r}")
            if python_requirement is None or "3.12" not in str(python_requirement):
                blockers.append("platform_python_target_missing_3.12")
            optional = project.get("optional-dependencies", {})
            simulation = optional.get("simulation", []) if isinstance(optional, dict) else []
            declared = " ".join(str(item) for item in simulation)
            if "flygym==2.1.0" not in declared:
                blockers.append("platform_flygym_pin_missing")
            if "mujoco==3.9.0" not in declared:
                blockers.append("platform_mujoco_pin_missing")
        except (OSError, tomllib.TOMLDecodeError) as exc:
            blockers.append(f"platform_pyproject_invalid={type(exc).__name__}")
    else:
        blockers.append("platform_pyproject_missing")

    if missing:
        blockers.extend(f"missing:{relative}" for relative in missing)

    hook_source = platform_root / "src/drosophila_pd/experiments/healthy_baseline.py"
    if hook_source.is_file():
        try:
            hook_text = hook_source.read_text(encoding="utf-8")
        except OSError:
            hook_text = ""
        required_hook_tokens = (
            "perturbation.apply_to_action",
            "apply_locomotion_action",
            "sim.step()",
        )
        blockers.extend(
            f"platform_hook_token_missing:{token}"
            for token in required_hook_tokens
            if token not in hook_text
        )

    commit = _git_value(platform_root, "rev-parse", "HEAD")
    status_text = _git_value(platform_root, "status", "--short")
    git_commit = commit or None
    worktree_dirty = bool(status_text) if commit else None
    if not platform_root.is_dir():
        blockers.insert(0, "platform_root_missing")

    capabilities = tuple(
        name
        for name, relative in (
            ("perturbation_protocol", "src/drosophila_pd/perturbations/base.py"),
            ("healthy_baseline", "scripts/run_healthy_baseline.py"),
            ("brain_driven_bridge", "scripts/run_brain_driven_experiment.py"),
            ("canonical_locomotion_hook", "src/drosophila_pd/experiments/healthy_baseline.py"),
        )
        if (platform_root / relative).is_file()
    )
    status = "READY" if not blockers else "WAITING_PLATFORM_CAPABILITY"
    return PlatformContract(
        root=str(platform_root),
        status=status,
        package_name=package_name,
        package_version=package_version,
        python_requirement=python_requirement,
        git_commit=git_commit,
        worktree_dirty=worktree_dirty,
        capabilities=capabilities,
        missing_files=missing,
        blockers=tuple(sorted(set(blockers))),
    )


def _git_value(root: Path, *args: str) -> str:
    if not root.is_dir():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


__all__ = [
    "PLATFORM_REQUIRED_FILES",
    "PlatformContract",
    "default_platform_root",
    "inspect_platform",
]
