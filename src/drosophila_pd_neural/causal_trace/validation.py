"""Fail-closed validation for Gate29 trace data."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np

from .schema import TRACE_ATOL, TRACE_RTOL
from .types import TraceEdge, TraceStep


class TraceValidationError(ValueError):
    """Raised when a trace violates a frozen engineering contract."""


def validate_trace_steps(steps: Iterable[TraceStep]) -> None:
    rows = tuple(steps)
    previous: TraceStep | None = None
    for row in rows:
        if previous is not None:
            if row.step_index != previous.step_index + 1:
                raise TraceValidationError("step_index is not monotonic by one.")
            if row.pre_time_s <= previous.pre_time_s:
                raise TraceValidationError("pre_time_s is not increasing.")
            if row.post_time_s <= previous.post_time_s:
                raise TraceValidationError("post_time_s is not increasing.")
        if row.post_time_s <= row.pre_time_s:
            raise TraceValidationError("post_time_s must be greater than pre_time_s.")
        if not np.isfinite([row.pre_time_s, row.post_time_s]).all():
            raise TraceValidationError("trace timestamps must be finite.")
        previous = row


def _comparison(
    baseline: Any,
    traced: Any,
    *,
    discrete: bool,
    atol: float = TRACE_ATOL,
    rtol: float = TRACE_RTOL,
) -> dict[str, Any]:
    left = np.asarray(baseline)
    right = np.asarray(traced)
    result: dict[str, Any] = {
        "shape_baseline": list(left.shape),
        "shape_trace": list(right.shape),
        "discrete": discrete,
        "atol": atol,
        "rtol": rtol,
    }
    if left.shape != right.shape:
        result.update({"passed": False, "reason": "SHAPE_MISMATCH", "max_abs_diff": None})
        return result
    if discrete:
        passed = bool(np.array_equal(left, right))
        max_abs: float | None = 0.0 if passed else None
    else:
        if not (np.isfinite(left).all() and np.isfinite(right).all()):
            result.update({"passed": False, "reason": "NONFINITE_VALUE", "max_abs_diff": None})
            return result
        delta = np.abs(left.astype(float) - right.astype(float))
        max_abs = float(delta.max()) if delta.size else 0.0
        passed = bool(np.allclose(left, right, rtol=rtol, atol=atol))
    result.update({"passed": passed, "reason": "EXACT_OR_WITHIN_FROZEN_TOLERANCE", "max_abs_diff": max_abs})
    return result


def compare_trace_arrays(
    baseline_arrays: Mapping[str, Any],
    traced_arrays: Mapping[str, Any],
    comparisons: Iterable[tuple[str, str, bool]],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for baseline_key, trace_key, discrete in comparisons:
        if baseline_key not in baseline_arrays or trace_key not in traced_arrays:
            results[baseline_key] = {
                "passed": False,
                "reason": "REQUIRED_SIGNAL_UNAVAILABLE",
                "max_abs_diff": None,
            }
            continue
        results[baseline_key] = _comparison(
            baseline_arrays[baseline_key], traced_arrays[trace_key], discrete=discrete
        )
    return {
        "comparisons": results,
        "status": "TRACE_OBSERVATION_NONPERTURBING_PASS"
        if all(item.get("passed") for item in results.values())
        else "TRACE_OBSERVATION_NONPERTURBING_FAIL",
        "atol": TRACE_ATOL,
        "rtol": TRACE_RTOL,
        "discrete_comparison": "EXACT_EQUALITY",
    }


def validate_edge_registry(edges: Iterable[TraceEdge]) -> None:
    rows = tuple(edges)
    if not rows:
        raise TraceValidationError("Causal edge registry must not be empty.")
    for edge in rows:
        if edge.biological_causality_established:
            raise TraceValidationError(
                f"Biological causality is forbidden in Gate29: {edge.edge_id}"
            )
        if not edge.source_basis:
            raise TraceValidationError(f"Missing source basis: {edge.edge_id}")
