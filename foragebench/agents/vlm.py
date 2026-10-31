# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model agent: a vision-language model choosing skills (``foragebench.agents.vlm``).

``FORAGEBENCH_ORCHESTRATOR`` selects the orchestrator:

- ``scripted`` (default): a short fixed sequence, for smoke runs.
- ``openai``: any model behind an OpenAI-compatible endpoint, ``FORAGEBENCH_BASE_URL`` (default
  Google's for Gemini), the key in the environment variable named by ``FORAGEBENCH_API_KEY_ENV``
  (default ``GEMINI_API_KEY``; empty for a local server such as vLLM).
- ``qwen3_vl``: Qwen3-VL loaded in this process with transformers (no server needed).

``FORAGEBENCH_MODEL`` names the model; ``FORAGEBENCH_MAX_CALLS`` sets the call budget (default 40);
``FORAGEBENCH_MAX_TOKENS`` the reply budget, reasoning included (default 4096);
``FORAGEBENCH_POINTER`` the grounding query the model is trained on, ``qwen`` or ``gemini`` (default
from the model's name); ``FORAGEBENCH_THINKING=0`` or ``1`` turns a vLLM-served model's thinking off
or on. The client logs every turn (what the model was shown, its reply and thinking, each pointing
query) under the run's ``agent/`` folder.

    GEMINI_API_KEY=... FORAGEBENCH_ORCHESTRATOR=openai FORAGEBENCH_MODEL=gemini-robotics-er-1.5-preview \\
    ./isaaclab.sh -p -m foragebench run --episode dev/grid_table --track gt_localization --agent vlm --output ...

    FORAGEBENCH_ORCHESTRATOR=openai FORAGEBENCH_BASE_URL=http://localhost:8000/v1 FORAGEBENCH_API_KEY_ENV= \\
    FORAGEBENCH_MODEL=Qwen/Qwen3.5-9B FORAGEBENCH_THINKING=0 ./isaaclab.sh -p -m foragebench run ...
"""

from __future__ import annotations

import os

from foragebench.agents.model.loop import LoopConfig, run_loop
from foragebench.agents.model.orchestrator import OrchestratorConfig, SkillCall


def orchestrator():
    kind = os.environ.get("FORAGEBENCH_ORCHESTRATOR", "scripted")
    model = os.environ.get("FORAGEBENCH_MODEL")
    pointer = os.environ.get("FORAGEBENCH_POINTER") or ("gemini" if "gemini" in (model or "").lower() else "qwen")
    thinking = os.environ.get("FORAGEBENCH_THINKING")  # 0 or 1; unset: the endpoint's default.
    config = OrchestratorConfig(
        model=model,
        pointer=pointer,
        max_new_tokens=int(os.environ.get("FORAGEBENCH_MAX_TOKENS", "4096")),
        thinking=None if not thinking else thinking == "1",
    )
    if kind == "scripted":
        from foragebench.agents.model.scripted import ScriptedOrchestrator

        return ScriptedOrchestrator([SkillCall("turn", {"yaw_rate": 0.4, "seconds": 2.0}), SkillCall("stow")])
    if kind == "qwen3_vl":
        from foragebench.agents.model.qwen3_vl import Qwen3VLOrchestrator

        return Qwen3VLOrchestrator(config if model else None)
    if kind == "openai":
        from foragebench.agents.model.openai_compatible import GEMINI, OpenAICompatibleOrchestrator

        return OpenAICompatibleOrchestrator(
            config,
            os.environ.get("FORAGEBENCH_BASE_URL", GEMINI),
            os.environ.get("FORAGEBENCH_API_KEY_ENV", "GEMINI_API_KEY") or None,
            log_dir=os.environ.get("FORAGEBENCH_AGENT_DIR"),
        )
    raise ValueError(f"Unknown FORAGEBENCH_ORCHESTRATOR {kind!r}: scripted, openai or qwen3_vl")


def run(session) -> None:
    budget = int(os.environ.get("FORAGEBENCH_MAX_CALLS", "40"))
    run_loop(session, orchestrator(), LoopConfig(max_calls=budget))
