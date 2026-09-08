"""Print the frozen Gate24E commands without executing or creating output."""

from __future__ import annotations

import subprocess

try:
    from scripts.prepare_gate24e_scientific_batch_plan import build_plan
except ModuleNotFoundError:  # direct ``python scripts/<tool>.py`` invocation
    from prepare_gate24e_scientific_batch_plan import build_plan


def main() -> int:
    plan = build_plan()
    print(f"status: {plan['status']}")
    print(f"job_count: {len(plan['jobs'])}")
    for job in plan["jobs"]:
        print(f"{job['job_index']:02d} {job['job_id']}: {subprocess.list2cmdline(job['command'])}")
    print("executed: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
