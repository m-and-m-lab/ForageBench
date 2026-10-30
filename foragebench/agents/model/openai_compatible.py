# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Any model behind an OpenAI-compatible chat endpoint: one client for every model.

Gemini answers on Google's OpenAI-compatible endpoint; Qwen3-VL (or any open model) served locally
by vLLM answers on ``http://localhost:8000/v1``. The key is read from the environment variable the
caller names, never from a file. Uses ``requests`` only.
"""

from __future__ import annotations

import base64
import io
import os

import requests

from foragebench.agents.model.orchestrator import (
    Observation,
    Orchestrator,
    OrchestratorConfig,
    SkillCall,
    parse_skill_call,
    turn_text,
)

GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai"


def png_data_url(image) -> str:
    """An HxWx3 uint8 image as a base64 PNG data URL."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


class OpenAICompatibleOrchestrator(Orchestrator):
    """``base_url`` (e.g. :data:`GEMINI` or ``http://localhost:8000/v1``), the model in
    ``config.model``, the key in the environment variable ``api_key_env`` (none for a local server)."""

    def __init__(self, config: OrchestratorConfig, base_url: str, api_key_env: str | None = None, timeout=300.0):
        super().__init__(config)
        if not config.model:
            raise ValueError("Name the model (FORAGEBENCH_MODEL).")
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        if api_key_env and not self.api_key:
            raise ValueError(f"Set the API key in the environment variable {api_key_env}.")
        self.replies: list[str] = []  # Every reply, for the run's log.
        self.usage: list[dict] = []  # The endpoint's token counts per call, when it gives them.

    def act(self, observation: Observation) -> SkillCall:
        content = [{"type": "text", "text": turn_text(observation, self.config.history)}]
        for name, image in observation.images.items():
            content.append({"type": "text", "text": f"Camera {name!r}, {image.shape[1]}x{image.shape[0]} px:"})
            content.append({"type": "image_url", "image_url": {"url": png_data_url(image)}})
        body = dict(
            model=self.config.model,
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": content}],
            max_tokens=self.config.max_new_tokens,
            temperature=0.0,
        )
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = requests.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"] or ""
        self.replies.append(text)
        self.usage.append(data.get("usage") or {})
        return parse_skill_call(text)
