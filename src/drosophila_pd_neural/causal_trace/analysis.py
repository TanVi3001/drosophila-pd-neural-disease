"""Neutral summaries for Gate29 signals."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np


def summarize_array(value: Any) -> dict[str, Any]:
    array = np.asarray(value)
    numeric = np.asarray(array, dtype=float) if np.issubdtype(array.dtype, np.number) else None
    if numeric is None or numeric.size == 0:
        return {
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "finite_fraction": None,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "nonzero_fraction": None,
            "change_count": None,
        }
    finite = np.isfinite(numeric)
    finite_values = numeric[finite]
    changes = np.diff(numeric.reshape(-1)) if numeric.size > 1 else np.array([])
    return {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "finite_fraction": float(finite.mean()),
        "min": float(finite_values.min()) if finite_values.size else None,
        "max": float(finite_values.max()) if finite_values.size else None,
        "mean": float(finite_values.mean()) if finite_values.size else None,
        "std": float(finite_values.std()) if finite_values.size else None,
        "nonzero_fraction": float(np.count_nonzero(numeric) / numeric.size),
        "change_count": int(np.count_nonzero(changes)) if changes.size else 0,
    }


def summarize_trace_arrays(arrays: Mapping[str, Any]) -> dict[str, Any]:
    return {name: summarize_array(value) for name, value in arrays.items()}
