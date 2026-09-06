"""Build an auditable, conservative mapping provenance package for Gate 20B."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"
ROOT_AUDIT_PATH = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
MAPPING_STATUS_PATH = ROOT / "research/disease_mapping/mapping_status.csv"
ANNOTATIONS_PATH = ROOT / "annotations/neuron_annotations.csv"
CONDITION_CONFIG_DIR = ROOT / "configs/conditions"
EXPORT_ROOT = ROOT / "research/disease_mapping/exports"
OUTPUT_ROOT = ROOT / "experiments/gate_20b_real_mapping_provenance"
REPORT_PATH = ROOT / "docs/disease_mapping/gate_20b_real_mapping_provenance_report.md"

CONDITIONS: dict[str, dict[str, str]] = {
    "alpha_synuclein": {
        "gene": "alpha_synuclein",
        "mapping_level": "PAN_NEURONAL_ORGANISM_LEVEL",
        "rollout_scope": "ORGANISM_LEVEL_PROXY_ONLY",
        "decision": "MODEL_SCOPE_NOT_CELL_SPECIFIC",
        "blocker": "Pan-neuronal expression does not identify a reviewed condition-specific root-ID set.",
        "paper_url": "https://pubmed.ncbi.nlm.nih.gov/24239353/",
        "paper_name": "Riemensperger et al. 2013, alpha-synuclein locomotion study",
    },
    "pink1": {
        "gene": "PINK1",
        "mapping_level": "WHOLE_ANIMAL_ORGANISM_LEVEL",
        "rollout_scope": "ORGANISM_LEVEL_PROXY_ONLY",
        "decision": "MODEL_SCOPE_NOT_CELL_SPECIFIC",
        "blocker": "The whole-animal mutant does not identify a reviewed neuron or edge intervention.",
        "paper_url": "https://pubmed.ncbi.nlm.nih.gov/16672981/",
        "paper_name": "Clark et al. 2006, PINK1 model",
    },
    "parkin": {
        "gene": "Parkin",
        "mapping_level": "DRIVER_OR_CLASS_LEVEL",
        "rollout_scope": "CLASS_LEVEL_EXPLORATORY_ONLY",
        "decision": "WAITING_REVIEWED_ROOT_ID_MAPPING",
        "blocker": "TH-GAL4 describes a class, but no reviewed TH-GAL4-to-FlyWire export is present.",
        "paper_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6673194/",
        "paper_name": "Sang et al. 2007, Parkin RNAi study",
    },
    "dj1": {
        "gene": "DJ-1",
        "mapping_level": "NOT_MAPPABLE_FROM_PAPER",
        "rollout_scope": "VALIDATION_ONLY",
        "decision": "NOT_MAPPABLE_FROM_PAPER",
        "blocker": "Behavioral evidence does not specify a neuron or edge intervention.",
        "paper_url": "https://doi.org/10.1016/j.gene.2005.06.040",
        "paper_name": "Tanti et al. 2005, DJ-1 behavioral mutant study",
    },
    "lrrk2": {
        "gene": "LRRK2",
        "mapping_level": "WAITING_VNC_CONNECTOME_MAPPING",
        "rollout_scope": "VALIDATION_ONLY",
        "decision": "WAITING_VNC_CONNECTOME_MAPPING",
        "blocker": "The cited scope requires motor-neuron/VNC coverage that is not present in the current brain-only catalog.",
        "paper_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2268198/",
        "paper_name": "Imai et al. 2008, LRRK2 locomotion study",
    },
}

PLACEHOLDER_IDS = (
    "TODO_ROOT_ID",
    "FAKE_ROOT_ID",
    "SYNTHETIC_ROOT",
    "000000",
    "TBD_ROOT",
    "MOCK_ROOT",
)

MAPPING_FIELDS = [
    "condition_id",
    "gene",
    "genotype",
    "driver",
    "model_scope",
    "mapping_level",
    "gene_specific_mapping",
    "allowed_rollout_scope",
    "connectome_name",
    "connectome_version",
    "root_id",
    "edge_id",
    "cell_type",
    "cell_class",
    "driver_scope",
    "anatomy_scope",
    "source_name",
    "source_url",
    "query_or_export_source",
    "query_string",
    "query_date",
    "source_sha256",
    "export_sha256",
    "paper_doi",
    "paper_pmid",
    "reviewer_1",
    "reviewer_2",
    "review_date",
    "decision",
    "blocker",
    "notes",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{str(key): str(value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _condition_key(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "alpha_synuclein_template": "alpha_synuclein",
        "pink1_template": "pink1",
        "parkin_template": "parkin",
        "dj1_template": "dj1",
        "lrrk2_template": "lrrk2",
    }
    return aliases.get(normalized, normalized)


def _config_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(CONDITION_CONFIG_DIR.glob("*.yaml")):
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if isinstance(document, dict):
            condition = _condition_key(str(document.get("condition_id", "")))
            if condition in CONDITIONS:
                paths[condition] = path
    return paths


def _paper_fields(provenance: str) -> tuple[str, str]:
    doi = ""
    pmid = ""
    for token in provenance.replace(";", " ").split():
        if token.lower().startswith("doi:"):
            doi = token.split(":", 1)[1].strip().rstrip(",")
        if token.lower().startswith("pmid:"):
            pmid = token.split(":", 1)[1].strip().rstrip(",")
    return doi, pmid


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"
    return result.stdout.strip()


def _required_input_rows() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    review_rows = {_condition_key(row.get("condition_id", "")): row for row in _rows(REVIEW_PATH)}
    root_rows = {_condition_key(row.get("condition_id", "")): row for row in _rows(ROOT_AUDIT_PATH)}
    status_rows = {_condition_key(row.get("condition_id", "")): row for row in _rows(MAPPING_STATUS_PATH)}
    missing = [condition for condition in CONDITIONS if condition not in review_rows or condition not in root_rows or condition not in status_rows]
    if missing:
        raise ValueError(f"Missing input rows for: {', '.join(missing)}")
    return review_rows, root_rows, status_rows


def _base_record(
    condition_id: str,
    review_row: dict[str, str],
    root_row: dict[str, str],
    status_row: dict[str, str],
) -> dict[str, Any]:
    profile = CONDITIONS[condition_id]
    reviewer = root_row.get("reviewer_2") or review_row.get("reviewer_2") or status_row.get("reviewer_2", "")
    review_date = root_row.get("review_date") or review_row.get("review_date") or status_row.get("review_date", "")
    paper_provenance = review_row.get("paper_provenance", "")
    doi, pmid = _paper_fields(paper_provenance)
    config_path = _config_paths().get(condition_id)
    model_scope = review_row.get("requested_model_scope") or root_row.get("literature_neural_scope", "")
    driver = review_row.get("driver_scope") or root_row.get("driver_or_genotype", "")
    genotype = root_row.get("gene_or_model") or review_row.get("gene_model", "")
    connectome_version = root_row.get("connectome_version", "")
    if not connectome_version:
        connectome_version = "FlyWire v783 (reference catalog only)"
    return {
        "condition_id": condition_id,
        "gene": profile["gene"],
        "genotype": genotype,
        "driver": driver,
        "model_scope": model_scope,
        "mapping_level": profile["mapping_level"],
        "gene_specific_mapping": False,
        "mapping_identifier_count": 0,
        "allowed_rollout_scope": profile["rollout_scope"],
        "connectome_name": "FlyWire",
        "connectome_version": connectome_version,
        "root_id": "",
        "edge_id": "",
        "cell_type": root_row.get("cell_type", "") or root_row.get("neuron_name", ""),
        "cell_class": root_row.get("cell_class", "") or root_row.get("literature_neural_scope", ""),
        "driver_scope": driver,
        "anatomy_scope": root_row.get("connectome_scope", ""),
        "source_name": profile["paper_name"],
        "source_url": profile["paper_url"],
        "query_or_export_source": "FlyWire annotations repository and Codex query/export were checked as permitted sources; no condition-specific export is present locally.",
        "query_string": "NOT_EXECUTED_NO_CONDITION_SPECIFIC_EXPORT",
        "query_date": "",
        "source_sha256": _sha256(ANNOTATIONS_PATH) if ANNOTATIONS_PATH.is_file() else "",
        "export_sha256": "",
        "paper_doi": doi,
        "paper_pmid": pmid,
        "reviewer_1": "",
        "reviewer_2": reviewer,
        "review_date": review_date,
        "decision": profile["decision"],
        "blocker": profile["blocker"],
        "notes": (
            "No root_id or edge_id is asserted. The local annotation table is a reference source, "
            "not a condition-specific driver-to-root export. Do not infer identifiers from gene, phenotype, "
            "driver name, or paper behavior."
        ),
        "config_path": str(config_path.relative_to(ROOT).as_posix()) if config_path else "",
        "root_audit_status": root_row.get("mapping_status", ""),
        "review_status": review_row.get("mapping_status", ""),
        "status_row_status": status_row.get("current_status", status_row.get("mapping_status", "")),
    }


def _write_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAPPING_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in MAPPING_FIELDS})


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")


def _condition_package(record: dict[str, Any]) -> dict[str, Any]:
    condition_id = str(record["condition_id"])
    package_dir = EXPORT_ROOT / condition_id
    export_path = package_dir / "mapping_export.csv"
    review_path = package_dir / "mapping_review.json"
    source_path = package_dir / "source_manifest.json"
    _write_csv(export_path, record)
    export_hash = _sha256(export_path)
    record["export_sha256"] = export_hash
    mapping_review = {
        "schema_version": "gate-20b-mapping-review-v1",
        "condition_id": condition_id,
        "mapping_level": record["mapping_level"],
        "gene_specific_mapping": False,
        "mapping_identifier_count": 0,
        "root_id_count": 0,
        "edge_id_count": 0,
        "decision": record["decision"],
        "allowed_rollout_scope": record["allowed_rollout_scope"],
        "connectome_version": record["connectome_version"],
        "source_export_path": export_path.relative_to(ROOT).as_posix(),
        "source_manifest_path": source_path.relative_to(ROOT).as_posix(),
        "source_sha256": record["source_sha256"],
        "export_sha256": export_hash,
        "reviewer_1": record["reviewer_1"],
        "reviewer_2": record["reviewer_2"],
        "review_date": record["review_date"],
        "human_signoff": "PENDING_HUMAN_SIGNOFF",
        "blocker": record["blocker"],
        "notes": record["notes"],
    }
    source_manifest = {
        "schema_version": "gate-20b-source-manifest-v1",
        "condition_id": condition_id,
        "source_name": record["source_name"],
        "source_url": record["source_url"],
        "source_urls": [
            record["source_url"],
            "https://github.com/flyconnectome/flywire_annotations",
            "https://codex.flywire.ai/faq",
        ],
        "source_file": "annotations/neuron_annotations.csv",
        "source_sha256": record["source_sha256"],
        "source_status": "REFERENCE_ONLY_NO_CONDITION_SPECIFIC_EXPORT",
        "query_or_export_source": record["query_or_export_source"],
        "query_string": record["query_string"],
        "query_date": record["query_date"],
        "connectome_name": record["connectome_name"],
        "connectome_version": record["connectome_version"],
        "mapping_level": record["mapping_level"],
        "gene_specific_mapping": False,
        "mapping_export": export_path.relative_to(ROOT).as_posix(),
        "export_sha256": export_hash,
        "reviewer_1": record["reviewer_1"],
        "reviewer_2": record["reviewer_2"],
        "review_date": record["review_date"],
        "decision": record["decision"],
        "human_signoff": "PENDING_HUMAN_SIGNOFF",
        "large_external_dump_committed": False,
        "blocker": record["blocker"],
        "notes": "The public source is recorded for provenance; it does not establish this condition's neuron target.",
    }
    _write_json(review_path, mapping_review)
    _write_json(source_path, source_manifest)
    return {
        "record": record,
        "export_path": export_path,
        "review_path": review_path,
        "source_path": source_path,
        "mapping_review": mapping_review,
        "source_manifest": source_manifest,
    }


def _validate_condition_configs(records: list[dict[str, Any]]) -> None:
    for item in records:
        record = item["record"]
        config_path = ROOT / record["config_path"]
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(config, dict):
            raise ValueError(f"Condition config must be a mapping: {config_path}")
        target_neurons = list(config.get("target_neurons") or [])
        target_edges = list(config.get("target_edges") or [])
        serialized_targets = json.dumps(target_neurons + target_edges, ensure_ascii=False)
        if any(token.lower() in serialized_targets.lower() for token in PLACEHOLDER_IDS):
            raise ValueError(f"Placeholder mapping ID found in {config_path}")
        class_level_config = (
            config.get("mapping_status") == "APPROVED_FOR_CLASS_LEVEL_EXPLORATORY"
            and config.get("mapping_level") == "DRIVER_OR_CLASS_LEVEL"
            and config.get("gene_specific_mapping") is False
            and config.get("allowed_rollout_scope") == "CLASS_LEVEL_EXPLORATORY_ONLY"
        )
        if (
            int(record["mapping_identifier_count"]) == 0
            and (target_neurons or target_edges)
            and not class_level_config
        ):
            raise ValueError(f"Config has targets but mapping export has no identifiers: {config_path}")
        approved = str(record["decision"]).startswith("APPROVED")
        if approved:
            if not target_neurons and not target_edges:
                raise ValueError(f"Approved condition lacks target_neurons/target_edges: {config_path}")
            if not config.get("full_burden"):
                raise ValueError(f"Approved condition lacks full_burden: {config_path}")
            if not config.get("burden_curve"):
                raise ValueError(f"Approved condition lacks burden_curve: {config_path}")
            if not config.get("provenance"):
                raise ValueError(f"Approved condition lacks provenance: {config_path}")
            if not record["reviewer_2"] or not _valid_date(record["review_date"]):
                raise ValueError(f"Approved condition lacks reviewer/date: {config_path}")
            if not record["source_sha256"] or not record["export_sha256"]:
                raise ValueError(f"Approved condition lacks source/export hash: {config_path}")
        if record["mapping_level"] in {
            "PAN_NEURONAL_ORGANISM_LEVEL",
            "WHOLE_ANIMAL_ORGANISM_LEVEL",
            "DRIVER_OR_CLASS_LEVEL",
        } and bool(record["gene_specific_mapping"]):
            raise ValueError(f"Broad mapping cannot be gene-specific: {config_path}")


def _validate_package_hashes(records: list[dict[str, Any]]) -> None:
    if not ANNOTATIONS_PATH.is_file():
        raise ValueError(f"Missing source annotation file: {ANNOTATIONS_PATH}")
    source_hash = _sha256(ANNOTATIONS_PATH)
    for item in records:
        record = item["record"]
        export_path = item["export_path"]
        review_path = item["review_path"]
        source_path = item["source_path"]
        if record["source_sha256"] != source_hash:
            raise ValueError(f"Source SHA256 mismatch for {record['condition_id']}")
        export_hash = _sha256(export_path)
        review = json.loads(review_path.read_text(encoding="utf-8"))
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if review.get("export_sha256") != export_hash or source.get("export_sha256") != export_hash:
            raise ValueError(f"Export SHA256 mismatch for {record['condition_id']}")
        if source.get("source_sha256") != source_hash:
            raise ValueError(f"Source manifest SHA256 mismatch for {record['condition_id']}")
        if not source.get("source_urls"):
            raise ValueError(f"Source URLs missing for {record['condition_id']}")
        if source.get("query_string", "").startswith("NOT_EXECUTED") and source.get("query_date"):
            raise ValueError(f"Query date must be empty for unexecuted query: {record['condition_id']}")


def _write_report(records: list[dict[str, Any]], starting: dict[str, str]) -> None:
    lines = [
        "# Gate 20B - Real Mapping Provenance Report",
        "",
        "## 1. Objective",
        "",
        "Gate 20B tạo package provenance cho mapping disease, nhưng không chạy GPU, simulation, calibration hoặc tuning.",
        "Mục tiêu là phân biệt mapping thật, mapping class-level và khoảng trống provenance trước khi mở disease rollout.",
        "",
        "## 2. Starting status",
        "",
        f"- Gene-specific mapping review: `{starting['gene_review']}`.",
        f"- Disease mapping: `{starting['disease_mapping']}`.",
        "- Mapping identifier count trước Gate 20B: `0` cho 5 condition disease.",
        "- Condition được duyệt trước Gate 20B: `0/5`.",
        "",
        "## 3. Evidence source policy",
        "",
        "Chỉ chấp nhận root ID/edge ID từ FlyWire annotations, Codex query/export, connectome annotation hoặc paper/supplementary có mapping cụ thể.",
        "Không suy ra ID từ gene name, genotype, driver name, phenotype hoặc hành vi. Bảng annotation local được ghi hash để truy vết, nhưng không được coi là mapping condition-specific.",
        "Nguồn công khai được ghi trong từng `source_manifest.json`: FlyWire annotations và Codex documentation/query path.",
        "",
        "## 4. Condition review table",
        "",
        "| Condition | Mapping level | Identifier count | Decision | Rollout scope | Blocker |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for item in records:
        record = item["record"]
        lines.append(
            f"| `{record['condition_id']}` | `{record['mapping_level']}` | `0` | `{record['decision']}` | `{record['allowed_rollout_scope']}` | {record['blocker']} |"
        )
    lines.extend(
        [
            "",
            "## 5. Approved or ready condition",
            "",
            "Chưa có condition nào được approve. Không condition nào có root ID hoặc edge ID thật được review cho disease intervention trong package này.",
            "Vì vậy Gate 21 disease rollout chưa được mở; trạng thái đúng là `MAPPING_REVIEW_BLOCKED_WITH_PROVENANCE_GAP` và `DISEASE_MAPPING_BLOCKED`.",
            "Parkin là ứng viên class-level đáng ưu tiên kiểm tra tiếp, nhưng vẫn cần export TH-GAL4/driver-to-root và reviewer signoff riêng.",
            "",
            "## 6. YAML updates",
            "",
            "Các condition YAML hiện vẫn là template không có target_neurons/target_edges. Gate 20B không thêm ID giả và không ghi đè healthy core.",
            "Mỗi package mapping export chỉ chứa một dòng metadata với identifier để trống; source manifest ghi rõ đây là reference-only.",
            "",
            "## 7. Audit result",
            "",
            "- `audit_gene_specific_mapping_review.py`: `MAPPING_REVIEW_BLOCKED`.",
            "- `audit_disease_mapping_readiness.py`: `DISEASE_MAPPING_BLOCKED`.",
            "- `audit_calibration_targets.py`: `READY_FOR_CALIBRATION` độc lập với disease mapping.",
            "- Không có simulation, calibration, tuning hoặc raw metric modification.",
            "",
            "## 8. Exact evidence still required",
            "",
            "1. Filtered FlyWire/Codex export có root ID hoặc edge ID thật cho từng intervention scope.",
            "2. Connectome version, cell type, anatomy scope và driver/expression scope của export.",
            "3. SHA-256 của export và query/export date.",
            "4. Reviewer thứ hai xác nhận scope và ký duyệt.",
            "5. Riêng LRRK2 cần VNC/motor-neuron mapping tương thích nếu muốn mở locomotion rollout.",
            "",
            "## 9. Scientific boundary",
            "",
            "Gate 20B chỉ xác nhận provenance/readiness của mapping tính toán.",
            "Gate này không xác nhận Parkinson sinh học, không xác nhận gene-specific disease mechanism, không phải clinical validation và không phải drug validation.",
            "Không được dùng package này để kết luận rằng disease rollout đã chạy hoặc đã có disease metrics.",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def _summary(records: list[dict[str, Any]], starting: dict[str, str]) -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    for item in records:
        record = item["record"]
        statuses[record["condition_id"]] = {
            "mapping_level": record["mapping_level"],
            "gene_specific_mapping": False,
            "mapping_identifier_count": 0,
            "decision": record["decision"],
            "rollout_scope": record["allowed_rollout_scope"],
            "blocker": record["blocker"],
            "mapping_export": item["export_path"].relative_to(ROOT).as_posix(),
            "source_manifest": item["source_path"].relative_to(ROOT).as_posix(),
        }
    return {
        "schema_version": "gate-20b-real-mapping-provenance-summary-v1",
        "status": "MAPPING_REVIEW_BLOCKED_WITH_PROVENANCE_GAP",
        "disease_mapping_status": "DISEASE_MAPPING_BLOCKED",
        "approved_condition_count": 0,
        "reviewed_condition_count": len(records),
        "starting_status": starting,
        "condition_statuses": statuses,
        "boundaries": {
            "biological_validation": False,
            "gene_specific_validation_by_default": False,
            "clinical_validation": False,
            "drug_validation": False,
        },
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "no_root_id_inference": True,
        "data_fabricated": False,
    }


def _manifest(records: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    source_paths = [
        "research/disease_mapping/gene_specific_mapping_review.csv",
        "datasets/literature_phenotypes/root_id_mapping_audit.csv",
        "research/disease_mapping/mapping_status.csv",
        "annotations/neuron_annotations.csv",
        "docs/claims/current_claim_lock.md",
    ]
    source_paths.extend(
        path.relative_to(ROOT).as_posix() for path in _config_paths().values()
    )
    generated_paths = [
        "docs/disease_mapping/gate_20b_real_mapping_provenance_report.md",
        "experiments/gate_20b_real_mapping_provenance/results/gate20b_mapping_summary.json",
    ]
    for item in records:
        generated_paths.extend(
            [
                item["export_path"].relative_to(ROOT).as_posix(),
                item["review_path"].relative_to(ROOT).as_posix(),
                item["source_path"].relative_to(ROOT).as_posix(),
            ]
        )
    hashes: dict[str, str] = {}
    for relative in source_paths + generated_paths:
        path = ROOT / relative
        if path.is_file():
            hashes[relative] = _sha256(path)
    return {
        "schema_version": "gate-20b-real-mapping-provenance-manifest-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": __import__("sys").version,
        "status": summary["status"],
        "disease_mapping_status": summary["disease_mapping_status"],
        "source_files": source_paths,
        "generated_files": generated_paths,
        "sha256": hashes,
        "review": {
            "reviewer_1": "",
            "reviewer_2": "Tuan Le",
            "review_date": "2026-09-06",
            "signoff": "PENDING_HUMAN_SIGNOFF",
        },
        "condition_decisions": summary["condition_statuses"],
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "large_artifacts_committed": False,
        "data_fabricated": False,
    }


def run(output_root: Path = OUTPUT_ROOT) -> int:
    review_rows, root_rows, status_rows = _required_input_rows()
    config_paths = _config_paths()
    missing_configs = sorted(set(CONDITIONS) - set(config_paths))
    if missing_configs:
        raise ValueError(f"Missing condition configs: {', '.join(missing_configs)}")
    starting = {
        "gene_review": "MAPPING_REVIEW_BLOCKED",
        "disease_mapping": "DISEASE_MAPPING_BLOCKED",
    }
    packages: list[dict[str, Any]] = []
    for condition_id in CONDITIONS:
        record = _base_record(condition_id, review_rows[condition_id], root_rows[condition_id], status_rows[condition_id])
        if record["reviewer_2"] and not _valid_date(record["review_date"]):
            raise ValueError(f"Invalid review date for {condition_id}: {record['review_date']}")
        package = _condition_package(record)
        packages.append(package)
    _validate_condition_configs(packages)
    _validate_package_hashes(packages)
    _write_report(packages, starting)
    summary = _summary(packages, starting)
    summary_path = output_root / "results/gate20b_mapping_summary.json"
    _write_json(summary_path, summary)
    manifest = _manifest(packages, summary)
    _write_json(output_root / "manifests/gate20b_mapping_manifest.json", manifest)
    print(f"Status: {summary['status']}")
    print(f"Disease mapping: {summary['disease_mapping_status']}")
    print(f"Approved conditions: {summary['approved_condition_count']}/{summary['reviewed_condition_count']}")
    print(f"Summary: {summary_path.resolve()}")
    print(f"Manifest: {(output_root / 'manifests/gate20b_mapping_manifest.json').resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args.output_root.resolve())
    except (OSError, ValueError, KeyError, TypeError, csv.Error, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
