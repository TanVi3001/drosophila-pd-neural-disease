from __future__ import annotations

from pathlib import Path

import pytest

import scripts.audit_gate24e_runtime_amendment as audit


def _guard_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "attempt_03"
    monkeypatch.setattr(audit, "ATTEMPT_03", root)
    return root


def test_pending_review_blocks_existing_empty_attempt_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _guard_root(monkeypatch, tmp_path)
    root.mkdir()
    assert audit._attempt03_review_blockers("PENDING") == [
        "attempt_03 exists while runtime amendment review is pending"
    ]


def test_approved_review_allows_absent_attempt_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _guard_root(monkeypatch, tmp_path)
    assert audit._attempt03_review_blockers("APPROVED") == []


def test_approved_review_allows_empty_attempt_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _guard_root(monkeypatch, tmp_path)
    root.mkdir()
    assert audit._attempt03_has_files() is False
    assert audit._attempt03_review_blockers("APPROVED") == []


def test_approved_review_blocks_attempt_directory_with_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _guard_root(monkeypatch, tmp_path)
    (root / "logs").mkdir(parents=True)
    (root / "logs" / "attempt.log").write_text("partial run\n", encoding="utf-8")
    assert audit._attempt03_has_files() is True
    assert audit._attempt03_review_blockers("APPROVED") == [
        "attempt_03 already contains execution artifacts"
    ]
