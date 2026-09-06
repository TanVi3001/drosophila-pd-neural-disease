"""Run Gate 20B mapping adjudication without changing scientific source data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_gene_specific_mapping_review import audit

DEFAULT_PLAN = ROOT / "experiments/gate_20b_mapping_adjudication/configs/mapping_adjudication_plan.yaml"
DEFAULT_INPUT = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"
DEFAULT_OUTPUT = ROOT / "experiments/gate_20b_mapping_adjudication"


def _write_report(path: Path, document: Mapping[str, Any], plan: Mapping[str, Any]) -> None:
    lines = [
        "# Gate 20B: Adjudication mapping gene-specific",
        "",
        f"**Trạng thái:** `{document['status']}`",
        "",
        "Gate này kiểm tra hồ sơ evidence để mở disease neural-first. Nó không tự suy ra root ID từ tên gene, không chạy simulation và không sửa healthy core.",
        "",
        f"- Condition cần adjudicate: `{document['condition_count']}`.",
        f"- Mapping đã APPROVED: `{document['approved_mapping_count']}`.",
        f"- Bằng chứng bắt buộc: `{', '.join(plan.get('required_evidence', []))}`.",
        "",
        "| Condition | Mapping status | Decision | Số identifier | Phạm vi được phép |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in document["conditions"]:
        lines.append(
            f"| `{row['condition_id']}` | `{row['mapping_status']}` | `{row['decision']}` | {row['mapping_identifier_count']} | {row['allowed_use']} |"
        )
    lines.extend(
        [
            "",
            "## Kết luận hiện tại",
            "",
            "Gate chưa mở Step 6 vì chưa có export root-ID/edge-ID gene-specific nào được reviewer xác nhận. 342 dopamine IDs hiện có chỉ được giữ ở class-level exploratory và không được gán cho PINK1, Parkin, DJ-1, LRRK2 hoặc alpha-synuclein.",
            "",
            "## Điều kiện chuyển tiếp",
            "",
            "Chỉ sau khi mỗi mapping có identifier export không rỗng, provenance truy lại được, cell/driver scope, connectome version, reviewer và ngày review hợp lệ thì mới cập nhật quyết định. Sau đó chạy lại Gate 20A trước khi chạy disease multi-seed.",
            "",
            "## Ranh giới khoa học",
            "",
            "Kết quả này không phải gene-specific biological Parkinson validation, không phải chẩn đoán và không thay thế thí nghiệm trên ruồi thật.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, plan_path: Path, input_path: Path, output_root: Path) -> int:
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    if not isinstance(plan, dict):
        raise ValueError("Gate 20B plan phai la YAML mapping.")
    document = audit(input_path.resolve())
    output_root.mkdir(parents=True, exist_ok=True)
    results = output_root / "results"
    manifests = output_root / "manifests"
    results.mkdir(exist_ok=True)
    manifests.mkdir(exist_ok=True)
    report = results / "mapping_adjudication.md"
    manifest = manifests / "mapping_adjudication_manifest.json"
    _write_report(report, document, plan)
    manifest_document = dict(document)
    manifest_document["plan"] = {
        "path": str(plan_path.resolve()),
        "sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
    }
    manifest_document["report"] = str(report.resolve())
    manifest.write_text(json.dumps(manifest_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Status: {document['status']}")
    print(f"Approved mappings: {document['approved_mapping_count']}/{document['condition_count']}")
    print(f"Report: {report.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(plan_path=args.plan, input_path=args.input, output_root=args.output_root)
    except (OSError, ValueError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
