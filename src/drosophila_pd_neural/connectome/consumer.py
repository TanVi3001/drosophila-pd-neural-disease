"""Promotion gates between connectome artifacts and the neural runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PromotionDecision:
    stage: str
    status: str
    reasons: tuple[str, ...]
    allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "reasons": list(self.reasons),
            "allowed": self.allowed,
        }


_STAGES = {
    "annotation_audit",
    "target_selection",
    "checkpoint_preparation",
    "rollout",
}


def evaluate_promotion(record: Mapping[str, Any], stage: str) -> PromotionDecision:
    """Evaluate whether a connectome record may enter a named project stage.

    This function is intentionally conservative. ``audit_only`` artifacts can
    support provenance and descriptive review, but cannot become a checkpoint or
    a rollout input without a verified mapping and an actual runtime consumer.
    """

    if stage not in _STAGES:
        raise ValueError(f"Unknown connectome promotion stage: {stage}")
    reasons: list[str] = []
    if not str(record.get("source_dataset", "")).strip():
        reasons.append("missing_source_dataset")
    if not str(record.get("id_namespace", "")).strip():
        reasons.append("missing_id_namespace")
    if not str(record.get("source_repo", "")).strip():
        reasons.append("missing_source_repo")
    if stage != "annotation_audit" and not str(record.get("sha256", "")).strip():
        reasons.append("missing_artifact_checksum")

    mapping_status = str(record.get("mapping_status", "unmapped"))
    target_reviewed = bool(record.get("target_reviewed", False))
    runtime_consumer = bool(record.get("runtime_consumer_available", False))

    if stage in {"checkpoint_preparation", "rollout"} and mapping_status != "verified":
        reasons.append("mapping_is_not_verified")
    if stage in {"checkpoint_preparation", "rollout"} and not target_reviewed:
        reasons.append("target_review_required")
    if stage == "rollout" and not runtime_consumer:
        reasons.append("platform_neural_consumer_unavailable")

    if reasons:
        return PromotionDecision(stage, "BLOCKED", tuple(reasons), False)
    if stage == "annotation_audit":
        return PromotionDecision(stage, "AUDIT_ONLY", (), True)
    if stage == "target_selection" and mapping_status != "verified":
        return PromotionDecision(stage, "CROSSMATCH_AUDIT_ONLY", (), True)
    if stage == "checkpoint_preparation":
        return PromotionDecision(stage, "CHECKPOINT_ELIGIBLE", (), True)
    return PromotionDecision(stage, "ROLLOUT_ELIGIBLE", (), True)
