from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research" / "literature_papers" / "source_manifest.json"
EXPECTED_EXTERNAL = {
    "godena_2014_lrrk2_microtubule",
    "hwang_2013_dj1_dlp",
    "pokrzywa_2017_alpha_syn_flytracker",
    "pozo_2022_pink1_serotonin",
}


def test_literature_manifest_externalizes_pdf_copies() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    papers = {paper["paper_id"]: paper for paper in payload["papers"]}

    assert EXPECTED_EXTERNAL <= papers.keys()
    for paper_id in EXPECTED_EXTERNAL:
        paper = papers[paper_id]
        assert paper["distribution"] == "external_download"
        assert paper["path"] is None
        assert paper["source_url"].startswith("https://")
        assert paper["expected_filename"].endswith(".pdf")
        assert paper["historical_local_size_bytes"] > 0
        digest = paper["historical_local_sha256"]
        assert len(digest) == hashlib.sha256().digest_size * 2
        assert all(char in "0123456789abcdef" for char in digest)

    assert papers["riemensperger_2011_dopamine_deficiency"]["distribution"] == "citation_only"


def test_literature_pdfs_are_not_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    tracked = {
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    }
    assert not any(
        path.startswith("research/literature_papers/open_access/") and path.endswith(".pdf")
        for path in tracked
    )
