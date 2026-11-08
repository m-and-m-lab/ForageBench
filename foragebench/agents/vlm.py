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
- ``claude``: Claude through Anthropic's Messages API (``pip install anthropic``; the key in
  ``ANTHROPIC_API_KEY``); the model defaults to ``claude-opus-5-5``, ``FORAGEBENCH_EFFORT`` sets how
  much it thinks per turn (low, medium, high, xhigh or max; default high).

``FORAGEBENCH_MODEL`` names the model; ``FORAGEBENCH_MAX_CALLS`` sets the call budget (default 40);
``FORAGEBENCH_MAX_TOKENS`` the reply budget, reasoning included (default 4096; 16000 for Claude);
``FORAGEBENCH_POINTER`` the grounding query the model is trained on, ``qwen``, ``gemini`` or ``claude``
(default from the model's name); ``FORAGEBENCH_THINKING=0`` or ``1`` turns a vLLM-served model's thinking off
or on. The run's ``agent/model.json`` holds the model, its settings and the hashes of what it is
asked (``result.json`` carries it). Every exchange with the model goes into the episode's recording
(``episode.rrd``, ``/agent/log/model/*``: the request, the raw response, the images as sent, what
the harness made of the reply, and every error with its origin; :class:`.model.orchestrator.TurnLog`).

    GEMINI_API_KEY=... FORAGEBENCH_ORCHESTRATOR=openai FORAGEBENCH_MODEL=gemini-robotics-er-1.5-preview \\
    isaaclab -p -m foragebench run --episode dev/grid_table --track gt_localization --agent vlm --output ...

    FORAGEBENCH_ORCHESTRATOR=openai FORAGEBENCH_BASE_URL=http://localhost:8000/v1 FORAGEBENCH_API_KEY_ENV= \\
    FORAGEBENCH_MODEL=Qwen/Qwen3.5-9B FORAGEBENCH_THINKING=0 isaaclab -p -m foragebench run ...

    ANTHROPIC_API_KEY=... FORAGEBENCH_ORCHESTRATOR=claude isaaclab -p -m foragebench run ...
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from foragebench.agents.model.loop import LoopConfig, run_loop
from foragebench.agents.model.orchestrator import OrchestratorConfig, SkillCall, prompt_hashes


def orchestrator():
    kind = os.environ.get("FORAGEBENCH_ORCHESTRATOR", "scripted")
    claude = kind == "claude"
    model = os.environ.get("FORAGEBENCH_MODEL") or ("claude-opus-5-5" if claude else None)
    family = next((name for name in ("gemini", "claude") if name in (model or "").lower()), "qwen")
    thinking = os.environ.get("FORAGEBENCH_THINKING")  # 0 or 1; unset: the endpoint's default.
    config = OrchestratorConfig(
        model=model,
        pointer=os.environ.get("FORAGEBENCH_POINTER") or family,
        max_new_tokens=int(os.environ.get("FORAGEBENCH_MAX_TOKENS") or (16000 if claude else 4096)),
        thinking=None if not thinking else thinking == "1",
        effort=os.environ.get("FORAGEBENCH_EFFORT") or None,
    )
    if kind == "scripted":
        from foragebench.agents.model.scripted import ScriptedOrchestrator

        return ScriptedOrchestrator(
            [SkillCall("command_velocity", {"v_x": 0.0, "v_y": 0.0, "v_rot": 0.4, "duration": 2.0}), SkillCall("stow")]
        )
    if kind == "openai":
        from foragebench.agents.model.openai_compatible import GEMINI, OpenAICompatibleOrchestrator

        return OpenAICompatibleOrchestrator(
            config,
            os.environ.get("FORAGEBENCH_BASE_URL", GEMINI),
            os.environ.get("FORAGEBENCH_API_KEY_ENV", "GEMINI_API_KEY") or None,
        )
    if claude:
        from foragebench.agents.model.claude import EFFORT, ClaudeOrchestrator

        config.effort = config.effort or EFFORT
        return ClaudeOrchestrator(config)
    raise ValueError(
        f"Unknown FORAGEBENCH_ORCHESTRATOR {kind!r}: scripted, openai (Gemini, or an open model) or claude"
    )


def settings(chosen, loop: LoopConfig) -> dict:
    """What produced a run: the orchestrator, the model and where it answered, every setting that
    changes what the model is asked, and the hashes of the prompt and the skill menu (the episode's
    system prompt itself is the recording's ``model/start``)."""
    config = chosen.config
    return dict(
        orchestrator=os.environ.get("FORAGEBENCH_ORCHESTRATOR", "scripted"),
        model=config.model,
        base_url=getattr(chosen, "base_url", None),
        pointer=config.pointer,
        thinking=config.thinking,
        effort=config.effort,
        max_new_tokens=config.max_new_tokens,
        history=config.history,
        max_calls=loop.max_calls,
        repeat_limit=loop.repeat_limit,
        **prompt_hashes(config.pointer, config.history),
    )


def run(session) -> None:
    budget = int(os.environ.get("FORAGEBENCH_MAX_CALLS", "40"))
    chosen, loop = orchestrator(), LoopConfig(max_calls=budget)
    setup = settings(chosen, loop)
    folder = os.environ.get("FORAGEBENCH_AGENT_DIR")  # The run's agent/ folder (eval/run.py sets it).
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / "model.json").write_text(json.dumps(setup, indent=1))
    session.log("model/setup", setup)
    run_loop(session, chosen, loop)
