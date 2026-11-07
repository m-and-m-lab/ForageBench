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

The key is read by the SDK from ``ANTHROPIC_API_KEY`` (or an ``ant auth login`` profile), never from a file.
"""

from __future__ import annotations

import base64
import io
import time
from pathlib import Path

from foragebench.agents.model.orchestrator import (
    Observation,
    Orchestrator,
    OrchestratorConfig,
    SkillCall,
    TurnLog,
    camera_label,
    parse_point,
    parse_skill_call,
    point_query,
    turn_text,
)

EFFORT = "high"  # A turn chooses the robot's next skill (the model's own default is medium).
POINT_EFFORT = "low"  # A grounding query, as the other families point with thinking off.
MAX_RETRIES = 5  # The SDK retries rate limits, overload and connection errors with backoff.
USAGE = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def png_block(image) -> dict:
    """An HxWx3 uint8 image as a base64 PNG image block."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    data = base64.b64encode(buffer.getvalue()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


def reply_text(response) -> tuple[str, str]:
    """A response's text and its thinking (summarized; empty when omitted)."""
    text = "".join(block.text for block in response.content if block.type == "text")
    thought = "\n".join(block.thinking for block in response.content if block.type == "thinking")
    return text, thought


class ClaudeOrchestrator(Orchestrator):
    """The model in ``config.model``; ``client`` an ``anthropic.Anthropic`` (made here when None)."""

    def __init__(self, config: OrchestratorConfig, client=None, log_dir: str | Path | None = None):
        super().__init__(config)
        if not config.model:
            raise ValueError("Name the model (FORAGEBENCH_MODEL).")
        if client is None:
            import anthropic

            client = anthropic.Anthropic(max_retries=MAX_RETRIES)
        self.client = client
        self.replies: list[str] = []  # Every reply, for the run's log.
        self.usage: list[dict] = []  # The token counts per turn.
        self.log = TurnLog(log_dir)  # Each turn's text, images, reply, thinking and timing, when a folder is given.

    def reset(self, brief: str, target_position: tuple[float, float, float] | None = None) -> None:
        super().reset(brief, target_position)
        self.log.start(self.system_prompt)  # The system prompt this episode, before its turns.

    def act(self, observation: Observation) -> SkillCall:
        content = [{"type": "text", "text": turn_text(observation, self.config.history)}]
        for name, image in observation.images.items():
            content.append({"type": "text", "text": camera_label(name, image)})
            content.append(png_block(image))
        system = [{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}]
        started = time.perf_counter()
        response = self._create(content, self.config.effort or EFFORT, "summarized", system=system)
        text, thought = reply_text(response)
        usage = {key: getattr(response.usage, key, None) for key in USAGE}
        self.replies.append(text)
        self.usage.append(usage)
        if thought:
            print(f"model thought ({len(thought)} chars): {thought[-1500:]}", flush=True)
        print(f"model reply: {text}", flush=True)
        seconds = time.perf_counter() - started
        self.log.turn(
            len(self.replies), observation, content[0]["text"], text, thought, response.stop_reason, usage, seconds
        )
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            raise ValueError(f"Claude declined to answer (refusal, category {category})")
        return parse_skill_call(text)

    def point(self, image, target: str) -> tuple[float, float] | None:
        """One image and the pixel query, at :data:`POINT_EFFORT`."""
        query = point_query(self.config.pointer, target, image.shape)
        started = time.perf_counter()
        response = self._create([png_block(image), {"type": "text", "text": query}], POINT_EFFORT, "omitted")
        text, _ = reply_text(response)
        point = parse_point(text, self.config.pointer, image.shape)
        print(f"model point: {target!r} -> {point} ({text.strip()[-120:]!r})", flush=True)
        self.log.point(len(self.replies), target, text, point, time.perf_counter() - started)
        return point

    def _create(self, content: list[dict], effort: str, display: str, **request):
        return self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_new_tokens,
            messages=[{"role": "user", "content": content}],
            thinking={"type": "adaptive", "display": display},
            output_config={"effort": effort},
            **request,
        )
