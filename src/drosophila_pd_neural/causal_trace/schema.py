"""Schema constants for committed Gate29 metadata and raw traces."""

from __future__ import annotations

TRACE_SCHEMA_VERSION = "gate29-neural-causal-trace-v1"
TRACE_ATOL = 1e-12
TRACE_RTOL = 0.0
GPU_STOP_TEMPERATURE_C = 82.0
GPU_MONITOR_INTERVAL_S = 1.0
TRACE_ARRAY_KEYS = (
    "step_index",
    "pre_time_s",
    "post_time_s",
    "dn_spikes",
    "decoder_rates_hz",
    "brain_body_drive",
    "controller_action_joint_angles",
    "controller_action_adhesion",
    "post_joint_positions",
    "post_joint_velocity",
    "post_actuator_position",
    "post_contact_found",
    "post_thorax_position_mm",
)
DISCRETE_TRACE_KEYS = ("step_index", "post_contact_found")
NONPERTURBATION_COMPARISONS = (
    ("timestamp_s", "post_time_s", False),
    ("thorax", "post_thorax_position_mm", False),
    ("joint_positions", "post_joint_positions", False),
    ("actuator_position", "post_actuator_position", False),
    ("contact_found", "post_contact_found", True),
)
