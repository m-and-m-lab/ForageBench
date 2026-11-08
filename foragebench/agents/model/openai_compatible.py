# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Any model behind an OpenAI-compatible chat endpoint: one client for every model.

Gemini answers on Google's OpenAI-compatible endpoint; Qwen3-VL (or any open model) served locally
by vLLM answers on ``http://localhost:8000/v1``. The key is read from the environment variable the
caller names, never from a file, and sent only in the request's header (the run's record keeps the
request body, never its headers). Uses ``requests`` only; it does not retry.
"""

from __future__ import annotations

import os
import time

import requests

from foragebench.agents.model.orchestrator import (
    Observation,
    Orchestrator,
    OrchestratorConfig,
    SkillCall,
    base64_text,
    camera_label,
    parse_point,
    parse_skill_call,
    point_query,
    turn_text,
    without_images,
)

GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai"


def png_data_url(png: bytes) -> str:
    """A PNG image as a base64 data URL."""
    return "data:image/png;base64," + base64_text(png)


class OpenAICompatibleOrchestrator(Orchestrator):
    """``base_url`` (e.g. :data:`GEMINI` or ``http://localhost:8000/v1``), the model in
    ``config.model``, the key in the environment variable ``api_key_env`` (none for a local server)."""

    def __init__(
        self,
        config: OrchestratorConfig,
        base_url: str,
        api_key_env: str | None = None,
        timeout=300.0,
    ):
        super().__init__(config)
        if not config.model:
            raise ValueError("Name the model (FORAGEBENCH_MODEL).")
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        if api_key_env and not self.api_key:
            raise ValueError(f"Set the API key in the environment variable {api_key_env}.")
        self.replies: list[str] = []  # Every reply.
        self.usage: list[dict] = []  # The endpoint's token counts per call, when it gives them.
        self._turn = 0

    def act(self, observation: Observation) -> SkillCall:
        self._turn = observation.turn
        images = self.log.encode(observation.images)
        content = [{"type": "text", "text": turn_text(observation, self.config.history)}]
        for name, image in observation.images.items():
            content.append({"type": "text", "text": camera_label(name, image)})
            content.append({"type": "image_url", "image_url": {"url": png_data_url(images[name])}})
        body = dict(
            model=self.config.model,
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": content}],
            max_tokens=self.config.max_new_tokens,
            temperature=0.0,
        )
        if self.config.thinking is not None:  # vLLM passes this to the chat template (Qwen3.x).
            body["chat_template_kwargs"] = {"enable_thinking": self.config.thinking}
        started = time.perf_counter()
        data, kept = self._post(body, images)
        message = data["choices"][0]["message"]
        text = message.get("content") or ""
        thought = message.get("reasoning_content") or message.get("reasoning") or ""  # vLLM's reasoning parser.
        self.replies.append(text)
        self.usage.append(data.get("usage") or {})
        if thought:
            print(f"model thought ({len(thought)} chars): {thought[-1500:]}", flush=True)
        print(f"model reply: {text}", flush=True)
        finish = data["choices"][0].get("finish_reason")
        seconds = round(time.perf_counter() - started, 3)
        usage = data.get("usage")
        self.log.turn(
            self._turn, images, text=text, thought=thought, finish=finish, usage=usage, seconds=seconds, **kept
        )
        return parse_skill_call(text)

    def point(self, image, target: str) -> tuple[float, float] | None:
        """One image and the model's own grounding query, thinking off (a vLLM-served model)."""
        query = point_query(self.config.pointer, target, image.shape)
        name, png = self.log.encoded(image)
        body = dict(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": png_data_url(png)}},
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
        data, kept = self._post(body, {name or "image": png})
        text = data["choices"][0]["message"].get("content") or ""
        point = parse_point(text, self.config.pointer, image.shape)
        print(f"model point: {target!r} -> {point} ({text.strip()[-120:]!r})", flush=True)
        seconds = round(time.perf_counter() - started, 3)
        self.log.point(self._turn, name, png, target=target, text=text, point=point, seconds=seconds, **kept)
        return point

    def _post(self, body: dict, images: dict[str, bytes]) -> tuple[dict, dict]:
        """The response's JSON and what the run's record keeps of the exchange: the request body (images
        by name), the raw response, its request id and the model that answered."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = requests.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as error:  # The server's own words go with it (the run's record keeps them).
            raise requests.HTTPError(f"{error}: {response.text[:2000]}", response=response) from error
        data = response.json()
        sent = {name: png_data_url(png) for name, png in images.items()}
        kept = dict(
            request=without_images(body, sent),
            response=data,
            request_id=response.headers.get("x-request-id") or data.get("id"),
            model=data.get("model"),
            retries=0,
        )
        return data, kept
