"""Tai brain source cong khai theo commit va kiem tra SHA256, khong chay mo phong."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen


SOURCE_REPOSITORY = "https://github.com/erojasoficial-byte/fly-brain"
SOURCE_COMMIT = "27cec28d5d202eb004683fb4c1a1033eec8deea0"
RAW_BASE = f"https://raw.githubusercontent.com/erojasoficial-byte/fly-brain/{SOURCE_COMMIT}/"
LFS_BASE = f"https://media.githubusercontent.com/media/erojasoficial-byte/fly-brain/{SOURCE_COMMIT}/"

# Kich thuoc va checksum la hop dong de khong vo tinh dung file tai thieu.
SOURCE_FILES = {
    "brain_body_bridge.py": {
        "url": RAW_BASE + "brain_body_bridge.py",
        "size": 34396,
        "sha256": "1ea350109fc5ffbae8baa54212fedc98267d70e2ea0c72f309572d25ba8c0a3f",
    },
    "code/run_pytorch.py": {
        "url": RAW_BASE + "code/run_pytorch.py",
        "size": 19180,
        "sha256": "333c09d54ee308e78916f20cc7ebca41d41e5307c7f5d7aab011a23bfc194c5b",
    },
    "code/benchmark.py": {
        "url": RAW_BASE + "code/benchmark.py",
        "size": 10972,
        "sha256": "c811c0d5dc91369ee6cff5ec9f7b18dd64dc692844046a4b5bde8a6503b84724",
    },
    "data/2025_Completeness_783.csv": {
        "url": RAW_BASE + "data/2025_Completeness_783.csv",
        "size": 3327347,
        "sha256": "bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311",
    },
    "data/2025_Connectivity_783.parquet": {
        "url": RAW_BASE + "data/2025_Connectivity_783.parquet",
        "size": 100804642,
        "sha256": "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347",
    },
    "data/flywire_annotations.tsv": {
        "url": RAW_BASE + "data/flywire_annotations.tsv",
        "size": 32638576,
        "sha256": "533db093e12d8de350fd20875a967f8f74acace633ff22118eefff550d5dcbc1",
    },
    "data/plastic_weights.pt": {
        "url": LFS_BASE + "data/plastic_weights.pt",
        "size": 60369156,
        "sha256": "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691",
    },
    "LICENSE": {
        "url": RAW_BASE + "LICENSE",
        "size": 1084,
        "sha256": "577e9dd0fdc76261bfeb61fbf694830cdff87f05752c3ef1255750d0eefa8eff",
    },
}


def _digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _download(url: str, destination: Path) -> None:
    partial = destination.with_name(destination.name + ".part")
    request = Request(url, headers={"User-Agent": "drosophila-pd-neural-disease"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(request, timeout=120) as response, partial.open("wb") as handle:
        while block := response.read(1024 * 1024):
            handle.write(block)
    partial.replace(destination)


def fetch_source(output: Path, *, include_checkpoint: bool = True) -> dict[str, object]:
    selected = {
        path: metadata
        for path, metadata in SOURCE_FILES.items()
        if include_checkpoint or path != "data/plastic_weights.pt"
    }
    records: list[dict[str, object]] = []
    for relative, metadata in selected.items():
        destination = output / relative
        if not destination.is_file() or destination.stat().st_size != metadata["size"]:
            print(f"Tai {relative} ...")
            _download(str(metadata["url"]), destination)
        actual_size = destination.stat().st_size
        actual_hash = _digest(destination)
        if actual_size != metadata["size"] or actual_hash != metadata["sha256"]:
            raise RuntimeError(
                f"Checksum khong khop cho {relative}: size={actual_size}, sha256={actual_hash}"
            )
        records.append({"path": relative, "size": actual_size, "sha256": actual_hash})
        print(f"OK {relative}")
    manifest = {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "code_license": "MIT",
        "data_license": "CC BY-NC 4.0",
        "files": records,
        "simulation_run": False,
    }
    (output / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-checkpoint",
        action="store_true",
        help="Chi tai ma va connectome, khong tai checkpoint LFS.",
    )
    args = parser.parse_args(argv)
    try:
        manifest = fetch_source(args.output.resolve(), include_checkpoint=not args.skip_checkpoint)
    except (OSError, RuntimeError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
