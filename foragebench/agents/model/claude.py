# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Claude through Anthropic's Messages API (the ``anthropic`` SDK, ``pip install anthropic``).

The same prompt, turn and reply as every other model (:mod:`.orchestrator`): each turn is one request
with the system prompt, the pose, the latest results and the camera images, and the reply is one
JSON object. What is Claude's own:

- It always thinks; ``config.effort`` (default :data:`EFFORT`) sets how much. The thinking comes back
  summarized, for the run's log. Claude takes no temperature: repeats differ.
- It points in the image's own pixels (:data:`.orchestrator.POINTERS` ``claude``), at :data:`POINT_EFFORT`.
- The system prompt is cached for the episode (it is the same every turn).
- A refusal is a reply with no skill (the model is told). There is no fallback to another model: a
  run is one model's.
- The run's record (:class:`.orchestrator.TurnLog`) keeps each request, the raw response body, its
  request id and the retries the SDK made.

The key is read by the SDK from ``ANTHROPIC_API_KEY`` (or an ``ant auth login`` profile), never from a file.
"""

from __future__ import annotations

import time

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

EFFORT = "high"  # A turn chooses the robot's next skill (the model's own default is medium).
POINT_EFFORT = "low"  # A grounding query, as the other families point with thinking off.
MAX_RETRIES = 5  # The SDK retries rate limits, overload and connection errors with backoff.
USAGE = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def png_block(png: bytes) -> dict:
    """A PNG image as a base64 image block."""
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_text(png)}}


def reply_text(response) -> tuple[str, str]:
    """A response's text and its thinking (summarized; empty when omitted)."""
    text = "".join(block.text for block in response.content if block.type == "text")
    thought = "\n".join(block.thinking for block in response.content if block.type == "thinking")
    return text, thought


class ClaudeOrchestrator(Orchestrator):
    """The model in ``config.model``; ``client`` an ``anthropic.Anthropic`` (made here when None)."""

    def __init__(self, config: OrchestratorConfig, client=None):
        super().__init__(config)
        if not config.model:
            raise ValueError("Name the model (FORAGEBENCH_MODEL).")
        if client is None:
            import anthropic

            client = anthropic.Anthropic(max_retries=MAX_RETRIES)
        self.client = client
        self.replies: list[str] = []  # Every reply.
        self.usage: list[dict] = []  # The token counts per turn.
        self._turn = 0

    def act(self, observation: Observation) -> SkillCall:
        self._turn = observation.turn
        images = self.log.encode(observation.images)
        content = [{"type": "text", "text": turn_text(observation, self.config.history)}]
        for name, image in observation.images.items():
            content.append({"type": "text", "text": camera_label(name, image)})
            content.append(png_block(images[name]))
        system = [{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}]
        started = time.perf_counter()
        response, kept = self._create(content, self.config.effort or EFFORT, "summarized", images, system=system)
        text, thought = reply_text(response)
        usage = {key: getattr(response.usage, key, None) for key in USAGE}
        self.replies.append(text)
        self.usage.append(usage)
        if thought:
            print(f"model thought ({len(thought)} chars): {thought[-1500:]}", flush=True)
        print(f"model reply: {text}", flush=True)
        finish = response.stop_reason
        seconds = round(time.perf_counter() - started, 3)
        self.log.turn(
            self._turn, images, text=text, thought=thought, finish=finish, usage=usage, seconds=seconds, **kept
        )
        if finish == "refusal":
            category = getattr(response.stop_details, "category", None)
            raise ValueError(f"Claude declined to answer (refusal, category {category})")
        return parse_skill_call(text)

    def point(self, image, target: str) -> tuple[float, float] | None:
        """One image and the pixel query, at :data:`POINT_EFFORT`."""
        query = point_query(self.config.pointer, target, image.shape)
        name, png = self.log.encoded(image)
        started = time.perf_counter()
        content = [png_block(png), {"type": "text", "text": query}]
        response, kept = self._create(content, POINT_EFFORT, "omitted", {name or "image": png})
        text, _ = reply_text(response)
        point = parse_point(text, self.config.pointer, image.shape)
        print(f"model point: {target!r} -> {point} ({text.strip()[-120:]!r})", flush=True)
        seconds = round(time.perf_counter() - started, 3)
        self.log.point(self._turn, name, png, target=target, text=text, point=point, seconds=seconds, **kept)
        return point

    def _create(self, content: list[dict], effort: str, display: str, images: dict[str, bytes], **options):
        """The message and what the run's record keeps of the exchange: the request (images by name),
        the raw response body, its request id, the model that answered and the SDK's retries."""
        request = dict(
            model=self.config.model,
            max_tokens=self.config.max_new_tokens,
            messages=[{"role": "user", "content": content}],
            thinking={"type": "adaptive", "display": display},
            output_config={"effort": effort},
            **options,
        )
        raw = self.client.messages.with_raw_response.create(**request)
        message = raw.parse()
        sent = {name: base64_text(png) for name, png in images.items()}
        kept = dict(
            request=without_images(request, sent),
            response=raw.http_response.json(),
            request_id=raw.request_id,
            model=getattr(message, "model", None),
            retries=raw.retries_taken,
        )
        return message, kept
