"""Abstract interface for disease-agnostic virtual assay adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .types import AdapterProvenance, ObservationWindow, RunObservation, TrajectoryData


class AssayAdapter(ABC):
    @abstractmethod
    def observe(
        self,
        trajectory: TrajectoryData,
        *,
        provenance: AdapterProvenance,
        window: ObservationWindow | None = None,
    ) -> RunObservation:
        """Convert an embodied trajectory into one run-level observation."""
