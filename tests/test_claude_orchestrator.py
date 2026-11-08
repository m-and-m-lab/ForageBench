# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The Claude client of the model harness, on a fake ``anthropic`` client: what it sends, how it
reads the reply, and how it points. No network and no SDK needed."""

from __future__ import annotations

import base64
import io
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from foragebench.agents.model.claude import ClaudeOrchestrator
from foragebench.agents.model.orchestrator import (
    Observation,
    OrchestratorConfig,
    SkillCall,
    TurnLog,
    parse_point,
    point_query,
)

WIDTH, HEIGHT = 480, 640  # The upright body cameras.


class FakeClient:
    """Answers each ``messages.with_raw_response.create`` as the SDK does (the raw response: its body,
    request id and retries; ``parse()`` the message) with the next reply text (or a refusal), and keeps
    the requests."""

    def __init__(self, *replies: str, stop_reason: str = "end_turn") -> None:
        self.replies, self.stop_reason, self.sent = list(replies), stop_reason, []
        self.messages = SimpleNamespace(with_raw_response=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.sent.append(request)
        thought = SimpleNamespace(type="thinking", thinking="fold the arm first", signature="s")
        text = SimpleNamespace(type="text", text=self.replies.pop(0))
        usage = SimpleNamespace(
            input_tokens=1500, output_tokens=900, cache_creation_input_tokens=0, cache_read_input_tokens=1100
        )
        details = SimpleNamespace(type="refusal", category="cyber") if self.stop_reason == "refusal" else None
        message = SimpleNamespace(
            content=[thought, text], stop_reason=self.stop_reason, stop_details=details, usage=usage, model="opus-x"
        )
        body = {"id": f"msg_{len(self.sent)}", "content": [{"type": "text", "text": text.text}]}
        return SimpleNamespace(
            parse=lambda: message,
            request_id=f"req_{len(self.sent)}",
            retries_taken=1,
            http_response=SimpleNamespace(json=lambda: body),
        )


class Kept:
    """What session.log would keep."""

    def __init__(self) -> None:
        self.logged = []

    def __call__(self, topic, record=None, images=None) -> None:
        self.logged.append((topic, record or {}, images or {}))


def orchestrator(client, kept=None) -> ClaudeOrchestrator:
    claude = ClaudeOrchestrator(
        OrchestratorConfig(model="claude-opus-5-5", pointer="claude", max_new_tokens=16000), client=client
    )
    claude.reset("the small green box", log=TurnLog(kept))
    return claude


def test_a_turn_sends_the_cached_prompt_the_named_images_and_the_effort_and_is_kept():
    client, kept = FakeClient('I will fold the arm.\n{"skill": "stow", "args": {}}'), Kept()
    claude = orchestrator(client, kept)
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    image[10, 20] = (255, 0, 0)
    observation = Observation(images={"frontleft": image, "hand": image}, pose=(1.0, 2.0, 0.5), turn=3)
    assert claude.act(observation) == SkillCall("stow")

    request = client.sent[0]
    assert request["model"] == "claude-opus-5-5" and request["max_tokens"] == 16000
    assert request["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert request["output_config"] == {"effort": "high"}
    assert "temperature" not in request  # Claude takes none.
    (system,) = request["system"]
    assert "Find and retrieve: the small green box" in system["text"] and system["cache_control"]["type"] == "ephemeral"
    (message,) = request["messages"]
    text, label, picture = message["content"][:3]
    assert "Your pose" in text["text"] and label["text"] == f"Camera 'frontleft', {WIDTH}x{HEIGHT} px:"
    from PIL import Image

    sent = np.asarray(Image.open(io.BytesIO(base64.b64decode(picture["source"]["data"]))))
    assert picture["source"]["media_type"] == "image/png" and np.array_equal(sent, image)  # Lossless, upright.
    assert [block["type"] for block in message["content"]] == ["text", "text", "image", "text", "image"]

    (_, start, _), (topic, turn, images) = kept.logged
    assert topic == "model/turn" and start["system_prompt"] == system["text"] and turn["turn"] == 3
    assert turn["thought"] == "fold the arm first" and turn["finish"] == "end_turn"
    assert turn["usage"]["cache_read_input_tokens"] == 1100 and turn["images"] == ["frontleft", "hand"]
    assert turn["request_id"] == "req_1" and turn["retries"] == 1 and turn["model"] == "opus-x"
    assert turn["response"]["id"] == "msg_1"  # The raw body.
    logged_picture = turn["request"]["messages"][0]["content"][2]
    assert logged_picture["source"]["data"] == "<image frontleft>" and turn["request"]["system"] == request["system"]
    assert base64.b64decode(picture["source"]["data"]) == images["frontleft"]  # The PNG kept is the PNG sent.
    assert json.dumps(turn)  # Plain JSON.


def test_claude_points_in_the_image_s_own_pixels_at_low_effort():
    client = FakeClient('```json\n[{"point": [120, 452], "label": "the handle"}]\n```', "I do not see it.")
    kept = Kept()
    claude = orchestrator(client, kept)
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    assert claude.point(image, "the handle") == pytest.approx((120.0, 452.0))
    assert claude.point(image, "a unicorn") is None
    request = client.sent[0]
    assert request["output_config"] == {"effort": "low"} and request["thinking"]["display"] == "omitted"
    picture, query = request["messages"][0]["content"]
    assert picture["type"] == "image" and query["text"] == point_query("claude", "the handle", image.shape)
    assert "the handle" in query["text"] and f"{WIDTH}x{HEIGHT} image" in query["text"]
    assert parse_point('[{"point": [900, -3]}]', "claude", image.shape) == (WIDTH - 1.0, 0.0)  # Kept in the image.
    (_, point, images), _ = [item for item in kept.logged if item[0] == "model/point"]
    assert point["image"] is None and tuple(point["point"]) == pytest.approx((120.0, 452.0))
    assert point["request"]["messages"][0]["content"][0]["source"]["data"] == "<image image>"
    assert base64.b64decode(picture["source"]["data"]) == images["image"]  # Not a turn's image: kept with it.


def test_a_refusal_is_a_reply_without_a_skill():
    claude = orchestrator(FakeClient("", stop_reason="refusal"))
    with pytest.raises(ValueError, match="declined"):
        claude.act(Observation(images={}, pose=None))


def test_a_claude_run_defaults_to_opus_high_effort_and_pixel_points(tmp_path, monkeypatch):
    from foragebench.agents import vlm

    made = []
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda **options: made.append(options)))
    monkeypatch.setenv("FORAGEBENCH_ORCHESTRATOR", "claude")
    monkeypatch.delenv("FORAGEBENCH_MODEL", raising=False)
    monkeypatch.delenv("FORAGEBENCH_MAX_TOKENS", raising=False)
    monkeypatch.delenv("FORAGEBENCH_POINTER", raising=False)
    monkeypatch.delenv("FORAGEBENCH_EFFORT", raising=False)
    monkeypatch.setenv("FORAGEBENCH_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.setattr(vlm, "run_loop", lambda session, chosen, loop: None)
    vlm.run(SimpleNamespace(log=Kept()))
    record = json.loads((tmp_path / "agent" / "model.json").read_text())
    assert record["orchestrator"] == "claude" and record["model"] == "claude-opus-5-5"
    assert record["pointer"] == "claude" and record["effort"] == "high" and record["max_new_tokens"] == 16000
    assert made == [{"max_retries": 5}]
