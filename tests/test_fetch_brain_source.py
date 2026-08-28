from scripts.fetch_brain_source import SOURCE_COMMIT, SOURCE_FILES


def test_source_manifest_is_pinned_and_complete() -> None:
    assert len(SOURCE_COMMIT) == 40
    assert SOURCE_FILES["data/2025_Connectivity_783.parquet"]["size"] > 100_000_000
    assert SOURCE_FILES["data/plastic_weights.pt"]["sha256"]
    assert SOURCE_FILES["code/benchmark.py"]["url"].endswith("code/benchmark.py")
