"""Mo hinh du lieu cho neural disease perturbation.

Day la mo hinh tinh toan co kiem soat, khong phai mo phong phan tu cua protein
hay ket luan ve co che sinh hoc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} phai la so huu han.")
    return result


@dataclass(frozen=True)
class NeuralParameters:
    """Tham so tai muc neural, khong phai gia tri dopamine."""

    presynaptic_gain: float = 1.0
    postsynaptic_gain: float = 1.0
    neuron_survival: float = 1.0
    energy_capacity: float = 1.0
    energy_consumption_scale: float = 1.0
    noise_std: float = 0.0
    action_delay_steps: int = 0

    def __post_init__(self) -> None:
        bounded = {
            "presynaptic_gain": self.presynaptic_gain,
            "postsynaptic_gain": self.postsynaptic_gain,
            "neuron_survival": self.neuron_survival,
            "energy_capacity": self.energy_capacity,
            "energy_consumption_scale": self.energy_consumption_scale,
            "noise_std": self.noise_std,
        }
        for name, value in bounded.items():
            number = _finite(name, value)
            if number < 0:
                raise ValueError(f"{name} khong duoc am.")
        for name in ("neuron_survival", "energy_capacity"):
            value = float(getattr(self, name))
            if value > 1.0:
                raise ValueError(f"{name} phai nam trong [0, 1].")
        if int(self.action_delay_steps) < 0:
            raise ValueError("action_delay_steps khong duoc am.")
        object.__setattr__(self, "presynaptic_gain", float(self.presynaptic_gain))
        object.__setattr__(self, "postsynaptic_gain", float(self.postsynaptic_gain))
        object.__setattr__(self, "neuron_survival", float(self.neuron_survival))
        object.__setattr__(self, "energy_capacity", float(self.energy_capacity))
        object.__setattr__(self, "energy_consumption_scale", float(self.energy_consumption_scale))
        object.__setattr__(self, "noise_std", float(self.noise_std))
        object.__setattr__(self, "action_delay_steps", int(self.action_delay_steps))

    def to_dict(self) -> dict[str, Any]:
        return {
            "presynaptic_gain": self.presynaptic_gain,
            "postsynaptic_gain": self.postsynaptic_gain,
            "neuron_survival": self.neuron_survival,
            "energy_capacity": self.energy_capacity,
            "energy_consumption_scale": self.energy_consumption_scale,
            "noise_std": self.noise_std,
            "action_delay_steps": self.action_delay_steps,
        }


@dataclass(frozen=True)
class DiseaseCondition:
    """Mot condition da duoc resolve tai mot tuoi va seed cu the."""

    condition_id: str
    gene_model: str
    age_days: float
    seed: int
    target_neurons: tuple[str, ...] = ()
    target_edges: tuple[tuple[str, str], ...] = ()
    parameters: NeuralParameters = field(default_factory=NeuralParameters)
    provenance: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not str(self.condition_id).strip():
            raise ValueError("condition_id khong duoc rong.")
        if not str(self.gene_model).strip():
            raise ValueError("gene_model khong duoc rong.")
        if _finite("age_days", self.age_days) < 0:
            raise ValueError("age_days khong duoc am.")
        if int(self.seed) < 0:
            raise ValueError("seed khong duoc am.")
        if len(set(self.target_neurons)) != len(self.target_neurons):
            raise ValueError("target_neurons khong duoc trung lap.")
        object.__setattr__(self, "age_days", float(self.age_days))
        object.__setattr__(self, "seed", int(self.seed))
        object.__setattr__(self, "target_neurons", tuple(str(x) for x in self.target_neurons))
        object.__setattr__(self, "target_edges", tuple((str(a), str(b)) for a, b in self.target_edges))
        object.__setattr__(self, "provenance", tuple(str(x) for x in self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "gene_model": self.gene_model,
            "age_days": self.age_days,
            "seed": self.seed,
            "target_neurons": list(self.target_neurons),
            "target_edges": [list(edge) for edge in self.target_edges],
            "parameters": self.parameters.to_dict(),
            "provenance": list(self.provenance),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DiseaseProfile:
    """Profile co duong cong burden chi khi nguoi dung cung cap diem moc."""

    condition_id: str
    gene_model: str
    seed: int
    target_neurons: tuple[str, ...] = ()
    target_edges: tuple[tuple[str, str], ...] = ()
    full_burden: NeuralParameters = field(default_factory=NeuralParameters)
    burden_curve: tuple[tuple[float, float], ...] = ()
    provenance: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        curve = tuple((float(age), float(burden)) for age, burden in self.burden_curve)
        if any(age < 0 or burden < 0 or burden > 1 for age, burden in curve):
            raise ValueError("burden_curve phai co age >= 0 va burden trong [0, 1].")
        if any(left[0] >= right[0] for left, right in zip(curve, curve[1:])):
            raise ValueError("burden_curve phai tang dan theo age_days.")
        object.__setattr__(self, "burden_curve", curve)

    def burden_at(self, age_days: float) -> float | None:
        """Noi suy burden giua cac moc thuc nghiem da duoc cung cap."""

        if not self.burden_curve:
            return None
        age = _finite("age_days", age_days)
        if age <= self.burden_curve[0][0]:
            return self.burden_curve[0][1]
        if age >= self.burden_curve[-1][0]:
            return self.burden_curve[-1][1]
        for (left_age, left_value), (right_age, right_value) in zip(
            self.burden_curve, self.burden_curve[1:]
        ):
            if left_age <= age <= right_age:
                fraction = (age - left_age) / (right_age - left_age)
                return left_value + fraction * (right_value - left_value)
        return None

    def at_age(self, age_days: float) -> DiseaseCondition | None:
        burden = self.burden_at(age_days)
        if burden is None:
            return None
        full = self.full_burden
        params = NeuralParameters(
            presynaptic_gain=1.0 + burden * (full.presynaptic_gain - 1.0),
            postsynaptic_gain=1.0 + burden * (full.postsynaptic_gain - 1.0),
            neuron_survival=1.0 - burden * (1.0 - full.neuron_survival),
            energy_capacity=1.0 - burden * (1.0 - full.energy_capacity),
            energy_consumption_scale=1.0 + burden * (full.energy_consumption_scale - 1.0),
            noise_std=burden * full.noise_std,
            action_delay_steps=round(burden * full.action_delay_steps),
        )
        return DiseaseCondition(
            condition_id=self.condition_id,
            gene_model=self.gene_model,
            age_days=float(age_days),
            seed=self.seed,
            target_neurons=self.target_neurons,
            target_edges=self.target_edges,
            parameters=params,
            provenance=self.provenance,
            notes=self.notes,
        )


def profile_from_mapping(data: Mapping[str, Any]) -> DiseaseProfile:
    """Parse YAML/JSON mapping ma khong tu tao target khoa hoc."""

    raw_params = data.get("full_burden", {}) or {}
    params = NeuralParameters(**raw_params)
    raw_curve = data.get("burden_curve", []) or []
    curve = tuple((float(row["age_days"]), float(row["burden"])) for row in raw_curve)
    edges = tuple((str(row["pre"]), str(row["post"])) for row in data.get("target_edges", []) or [])
    return DiseaseProfile(
        condition_id=str(data["condition_id"]),
        gene_model=str(data["gene_model"]),
        seed=int(data.get("seed", 0)),
        target_neurons=tuple(str(x) for x in data.get("target_neurons", []) or []),
        target_edges=edges,
        full_burden=params,
        burden_curve=curve,
        provenance=tuple(str(x) for x in data.get("provenance", []) or []),
        notes=str(data.get("notes", "")),
    )
