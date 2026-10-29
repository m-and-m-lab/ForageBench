# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model-agent harness: a vision-language model choosing skills through the session.

:mod:`.orchestrator` (prompt, skill-call parsing), :mod:`.skills` (the skills, each a few session
calls), :mod:`.loop` (observe, choose, run, repeat), and the orchestrators: :mod:`.scripted` (a
fixed list of calls, for tests and smoke runs), :mod:`.qwen3_vl` (local, transformers) and
:mod:`.gemini_robotics_er` (Google GenAI SDK). The agent entry point is ``foragebench.agents.vlm``
(``FORAGEBENCH_ORCHESTRATOR`` picks the orchestrator).
"""
