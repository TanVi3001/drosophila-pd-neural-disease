"""Load and validate the reviewed Parkin driver-defined root-ID set."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
from pathlib import Path


EXPECTED_MAPPING_LEVEL = "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED"
EXPECTED_ROOT_COUNT = 330


class MappingValidationError(ValueError):
    """Raised when reviewed mapping provenance is incomplete or changes."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def root_set_sha256(root_ids: tuple[str, ...] | list[str]) -> str:
    values = sorted(str(value) for value in root_ids)
    return hashlib.sha256(("\n".join(values) + "\n").encode("utf-8")).hexdigest()


def _valid_reviewer(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.upper() not in {"TODO", "TBD", "PENDING", "UNKNOWN"}


@dataclass(frozen=True)
class ReviewedParkinMapping:
    """Immutable provenance for the 330 reviewed target root IDs."""

    path: Path
    root_ids: tuple[str, ...]
    mapping_sha256: str
    root_set_sha256: str
    reviewer_1: str
    reviewer_2: str
    review_date: str

    @property
    def count(self) -> int:
        return len(self.root_ids)


def load_reviewed_mapping(
    path: Path,
    *,
    expected_mapping_sha256: str | None = None,
    expected_root_set_sha256: str | None = None,
) -> ReviewedParkinMapping:
    """Load only the exact reviewed 330-root mapping; never infer IDs."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) == 342:
        raise MappingValidationError("The 342-ID Riemensperger set is forbidden for Gate24 Parkin.")
    if len(rows) != EXPECTED_ROOT_COUNT:
        raise MappingValidationError(f"Expected exactly {EXPECTED_ROOT_COUNT} reviewed rows, got {len(rows)}.")
    required = {
        "root_id",
        "edge_id",
        "mapping_level",
        "reviewer_1",
        "reviewer_2",
        "review_date",
        "source_sha256",
        "export_sha256",
    }
    missing = sorted(required.difference(rows[0]))
    if missing:
        raise MappingValidationError(f"Mapping is missing required provenance columns: {missing}")
    root_ids = tuple(str(row.get("root_id", "")).strip() for row in rows)
    if any(not value.isdigit() for value in root_ids):
        raise MappingValidationError("Every target must have a numeric FlyWire root ID.")
    if len(set(root_ids)) != EXPECTED_ROOT_COUNT:
        raise MappingValidationError("Target root IDs must be unique and unchanged.")
    if any(str(row.get("edge_id", "")).strip() for row in rows):
        raise MappingValidationError("Gate24 accepts the reviewed neuron population only; edge IDs are not allowed.")
    if any(str(row.get("mapping_level", "")).strip() != EXPECTED_MAPPING_LEVEL for row in rows):
        raise MappingValidationError("Mapping level is not consistently driver-defined.")
    if any(not str(row.get(column, "")).strip() for row in rows for column in ("source_sha256", "export_sha256")):
        raise MappingValidationError("Every mapping row must retain source and export checksums.")
    reviewers_1 = {str(row.get("reviewer_1", "")).strip() for row in rows}
    reviewers_2 = {str(row.get("reviewer_2", "")).strip() for row in rows}
    dates = {str(row.get("review_date", "")).strip() for row in rows}
    if len(reviewers_1) != 1 or not _valid_reviewer(next(iter(reviewers_1))):
        raise MappingValidationError("Reviewer 1 provenance is incomplete.")
    if len(reviewers_2) != 1 or not _valid_reviewer(next(iter(reviewers_2))):
        raise MappingValidationError("Reviewer 2 provenance is incomplete.")
    if len(dates) != 1 or not next(iter(dates)):
        raise MappingValidationError("Review date provenance is incomplete.")
    mapping_sha = sha256_file(path)
    root_sha = root_set_sha256(root_ids)
    if expected_mapping_sha256 and mapping_sha != expected_mapping_sha256:
        raise MappingValidationError("Reviewed mapping SHA256 does not match the locked provenance.")
    if expected_root_set_sha256 and root_sha != expected_root_set_sha256:
        raise MappingValidationError("Reviewed root-ID set SHA256 does not match the locked provenance.")
    return ReviewedParkinMapping(
        path=path.resolve(),
        root_ids=root_ids,
        mapping_sha256=mapping_sha,
        root_set_sha256=root_sha,
        reviewer_1=next(iter(reviewers_1)),
        reviewer_2=next(iter(reviewers_2)),
        review_date=next(iter(dates)),
    )


def load_completeness_root_ids(path: Path) -> tuple[str, ...]:
    """Read the explicit FlyWire root-ID ordering used by the connectome."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or not rows[0]:
        raise MappingValidationError("Completeness CSV is empty.")
    root_ids = tuple(row[0].strip() for row in rows[1:] if row and row[0].strip())
    if len(root_ids) != len(set(root_ids)):
        raise MappingValidationError("Completeness CSV contains duplicate root IDs.")
    if any(not value.isdigit() for value in root_ids):
        raise MappingValidationError("Completeness CSV contains a non-numeric root ID.")
    return root_ids
