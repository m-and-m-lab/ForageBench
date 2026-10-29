# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model agent: a vision-language model choosing skills (``foragebench.agents.vlm``).

``FORAGEBENCH_ORCHESTRATOR`` selects the orchestrator: ``scripted`` (default; a short fixed
sequence, for smoke runs), ``qwen3_vl`` or ``gemini_robotics_er``. ``FORAGEBENCH_MODEL`` overrides
the model name; ``FORAGEBENCH_MAX_CALLS`` the call budget (default 40).

    ./isaaclab.sh -p $FORAGEBENCH/foragebench/eval/run.py --episode dev/grid_table --track gt_localization \\
        --agent vlm --output ...
"""

from __future__ import annotations

import os

from foragebench.agents.model.loop import LoopConfig, run_loop
from foragebench.agents.model.orchestrator import OrchestratorConfig, SkillCall


def orchestrator():
    kind = os.environ.get("FORAGEBENCH_ORCHESTRATOR", "scripted")
    model = os.environ.get("FORAGEBENCH_MODEL")
    config = OrchestratorConfig(model=model) if model else None
    if kind == "scripted":
        from foragebench.agents.model.scripted import ScriptedOrchestrator

        return ScriptedOrchestrator([SkillCall("turn", {"yaw_rate": 0.4, "seconds": 2.0}), SkillCall("stow")])
    if kind == "qwen3_vl":
        from foragebench.agents.model.qwen3_vl import Qwen3VLOrchestrator

        return Qwen3VLOrchestrator(config)
    if kind == "gemini_robotics_er":
        from foragebench.agents.model.gemini_robotics_er import GeminiRoboticsEROrchestrator

        return GeminiRoboticsEROrchestrator(config)
    raise ValueError(f"Unknown FORAGEBENCH_ORCHESTRATOR {kind!r}: scripted, qwen3_vl or gemini_robotics_er")


def run(session) -> None:
    budget = int(os.environ.get("FORAGEBENCH_MAX_CALLS", "40"))
    results = run_loop(session, orchestrator(), LoopConfig(max_calls=budget))
    for result in results:
        print(f"model agent: {result.call.name}{result.call.args} -> {result.status} {result.reason}")
