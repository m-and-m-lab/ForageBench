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
import json
import os
import time
from pathlib import Path

import requests

from foragebench.agents.model.orchestrator import (
    Observation,
    Orchestrator,
    OrchestratorConfig,
    SkillCall,
    parse_point,
    parse_skill_call,
    point_query,
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

    def __init__(
        self,
        config: OrchestratorConfig,
        base_url: str,
        api_key_env: str | None = None,
        timeout=300.0,
        log_dir: str | Path | None = None,
    ):
        super().__init__(config)
        if not config.model:
            raise ValueError("Name the model (FORAGEBENCH_MODEL).")
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        if api_key_env and not self.api_key:
            raise ValueError(f"Set the API key in the environment variable {api_key_env}.")
        self.replies: list[str] = []  # Every reply, for the run's log.
        self.usage: list[dict] = []  # The endpoint's token counts per call, when it gives them.
        # Each turn's text, images (JPEG), reply, thinking and timing, when a folder is given.
        self.log_dir = None if log_dir is None else Path(log_dir)

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
        if self.config.thinking is not None:  # vLLM passes this to the chat template (Qwen3.x).
            body["chat_template_kwargs"] = {"enable_thinking": self.config.thinking}
        started = time.perf_counter()
        data = self._post(body)
        message = data["choices"][0]["message"]
        text = message.get("content") or ""
        thought = message.get("reasoning_content") or message.get("reasoning") or ""  # vLLM's reasoning parser.
        self.replies.append(text)
        self.usage.append(data.get("usage") or {})
        if thought:
            print(f"model thought ({len(thought)} chars): {thought[-1500:]}", flush=True)
        print(f"model reply: {text}", flush=True)
        self._log(observation, content[0]["text"], text, thought, data, time.perf_counter() - started)
        return parse_skill_call(text)

    def point(self, image, target: str) -> tuple[float, float] | None:
        """One image and the model's own grounding query, thinking off (a vLLM-served model)."""
        query = point_query(self.config.pointer, target)
        body = dict(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": png_data_url(image)}},
                        {"type": "text", "text": query},
                    ],
                }
            ],
            max_tokens=self.config.max_new_tokens,
            temperature=0.0,
        )
        if self.config.thinking is not None:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        started = time.perf_counter()
        data = self._post(body)
        text = data["choices"][0]["message"].get("content") or ""
        point = parse_point(text, self.config.pointer, image.shape)
        print(f"model point: {target!r} -> {point} ({text.strip()[-120:]!r})", flush=True)
        if self.log_dir is not None:
            record = dict(turn=len(self.replies), kind="point", target=target, reply=text, point=point)
            record["seconds"] = round(time.perf_counter() - started, 2)
            with (self.log_dir / "turns.jsonl").open("a") as file:
                file.write(json.dumps(record) + "\n")
        return point

    def _post(self, body: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = requests.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _log(self, observation: Observation, sent: str, text: str, thought: str, data: dict, seconds: float) -> None:
        if self.log_dir is None:
            return
        from PIL import Image

        self.log_dir.mkdir(parents=True, exist_ok=True)
        turn = len(self.replies)
        for name, image in observation.images.items():
            Image.fromarray(image).save(self.log_dir / f"turn_{turn:03d}_{name}.jpg", quality=90)
        record = dict(
            kind="turn",
            turn=turn,
            seconds=round(seconds, 2),
            sent=sent,
            images=sorted(observation.images),
            reply=text,
            thought=thought,
            finish=data["choices"][0].get("finish_reason"),
            usage=data.get("usage"),
        )
        with (self.log_dir / "turns.jsonl").open("a") as file:
            file.write(json.dumps(record) + "\n")
