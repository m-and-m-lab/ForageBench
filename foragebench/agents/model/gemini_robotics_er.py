# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Gemini Robotics-ER orchestrator through the Google GenAI SDK (``pip install google-genai``).

Reads ``GEMINI_API_KEY`` from the environment. Untested against the API in this repository's CI.
"""

from __future__ import annotations

from foragebench.agents.model.orchestrator import (
    Observation,
    Orchestrator,
    OrchestratorConfig,
    SkillCall,
    history_text,
    parse_skill_call,
)


class GeminiRoboticsEROrchestrator(Orchestrator):
    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        super().__init__(config or OrchestratorConfig(model="gemini-robotics-er-1.5-preview"))
        from google import genai

        self.client = genai.Client()  # GEMINI_API_KEY from the environment.

    def act(self, observation: Observation) -> SkillCall:
        return parse_skill_call(self._generate(observation))

    def _generate(self, observation: Observation) -> str:
        from google.genai import types
        from PIL import Image

        parts = [Image.fromarray(image) for image in observation.images.values()]
        pose = "unknown" if observation.pose is None else [round(v, 3) for v in observation.pose]
        parts.append(
            f"Cameras (in order): {', '.join(observation.images)}. Your pose (x, y, heading): {pose}.\n"
            f"Previous skill results:\n{history_text(observation.history, self.config.history)}\n"
            "Reply with one JSON object."
        )
        response = self.client.models.generate_content(
            model=self.config.model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt, max_output_tokens=self.config.max_new_tokens
            ),
        )
        return response.text or ""
