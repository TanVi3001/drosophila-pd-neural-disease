"""Immutable, claim-safe contracts for Gate29 execution-path traces."""

from .analysis import summarize_array, summarize_trace_arrays
from .types import (
    DependencyClass,
    SignalAvailability,
    TraceEdge,
    TraceLayer,
    TraceProvenance,
    TraceStep,
    TraceSummary,
)
from .validation import (
    TRACE_ATOL,
    TRACE_RTOL,
    TraceValidationError,
    compare_trace_arrays,
    validate_edge_registry,
    validate_trace_steps,
)

__all__ = [
    "DependencyClass",
    "SignalAvailability",
    "TRACE_ATOL",
    "TRACE_RTOL",
    "TraceEdge",
    "TraceLayer",
    "TraceProvenance",
    "TraceStep",
    "TraceSummary",
    "TraceValidationError",
    "compare_trace_arrays",
    "summarize_array",
    "summarize_trace_arrays",
    "validate_edge_registry",
    "validate_trace_steps",
]
