from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".gitattributes",
    ".gitignore",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".tex",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
MOJIBAKE = re.compile(
    r"(?:[\u00C2-\u00C6\u00D0\u00D1\u0102][\u0080-\u00BF]"
    r"|\u00E2[\u0080-\u00BF\u201A\u20AC\u2122\u0153\u017E]"
    r"|\u00C3[\u0080-\u00BF]"
    r"|\u00C4[\u0080-\u00BF])"
)


def _tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / Path(raw.decode())
        for raw in result.stdout.split(b"\0")
        if raw and Path(raw.decode()).suffix.lower() in TEXT_SUFFIXES
    ]


def test_tracked_text_has_no_common_mojibake_sequences() -> None:
    failures: list[str] = []
    invalid_utf8: list[str] = []
    for path in _tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            invalid_utf8.append(str(path.relative_to(ROOT)))
            continue
        if MOJIBAKE.search(text):
            failures.append(str(path.relative_to(ROOT)))

    assert not invalid_utf8, f"Invalid UTF-8 files: {invalid_utf8}"
    assert not failures, f"Mojibake sequences found: {failures}"
