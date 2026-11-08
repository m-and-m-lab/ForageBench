# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Orchestrators: a model picks the next skill from the cameras, the brief and the history.

Carried over from the May beta (prompt template, argument-checked skill calls) and re-targeted at
PhyGS's session: a skill here is one of :mod:`.skills`, each a few session calls. The orchestrator
never touches the session itself; :mod:`.loop` runs it and gives it the run's :class:`TurnLog`.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any

from foragebench.agents.model.skills import SKILLS, SkillResult

PROMPTS = Path(__file__).resolve().parent / "prompts"


@dataclass(frozen=True)
class SkillCall:
    """One chosen skill with its arguments, as the model named them."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    model: str | None = None
    max_new_tokens: int = 4096  # A thinking model's reasoning counts too.
    history: int = 8  # How many past results the model sees.
    pointer: str = "qwen"  # The grounding query the model is trained on (:data:`POINTERS`).
    thinking: bool | None = None  # A vLLM-served model's thinking on or off (None: its default).
    effort: str | None = None  # How much Claude thinks per turn: low, medium, high, xhigh or max (None: high).


@dataclass
class Observation:
    """What the model is shown each turn: images by camera name (HxWx3 uint8), the robot's planar
    pose (x, y, heading) when the track grants it, the latest skill results, and the turn's number."""

    images: dict[str, Any]
    pose: tuple[float, float, float] | None
    history: list[SkillResult] = field(default_factory=list)
    turn: int = 0


class Orchestrator(ABC):
    """Picks the next skill; subclasses talk to a model."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self.system_prompt = ""
        self.log = TurnLog()  # The run's record (the loop gives it the session's); none until then.

    def reset(
        self, brief: str, target_position: tuple[float, float, float] | None = None, log: TurnLog | None = None
    ) -> None:
        """Start an episode: ``brief`` is the task's public description; ``target_position`` is
        given only on a track that grants the target's position; ``log`` keeps the run's record."""
        self.system_prompt = build_system_prompt(brief, target_position)
        self.log = log or TurnLog()
        self.log.start(self.system_prompt)

    @abstractmethod
    def act(self, observation: Observation) -> SkillCall:
        """Choose the next skill."""

    def point(self, image, target: str) -> tuple[float, float] | None:
        """Where ``target`` (a few words) is in ``image`` (HxWx3), in pixels (u, v); None when the
        model finds none."""
        raise NotImplementedError(f"{type(self).__name__} cannot point at a target named in words")


def skill_list() -> str:
    def forms(name: str) -> str:
        return " or ".join(f"{name}({', '.join(args)})" for args in model_forms(name))

    return "\n".join(f"- {forms(name)}: {skill.doc}" for name, skill in SKILLS.items())


POINTED = ("camera", "target")  # What a model names for a skill that acts at a point.
POINTERS = {  # The grounding query a model family is trained on: prompt, JSON key, order of the numbers,
    # and the grid the numbers are on (None: the image's own pixels).
    "qwen": (
        'Point to {target}. Output its point in JSON as [{{"point_2d": [x, y], "label": "{target}"}}].',
        "point_2d",
        "xy",
        1000,
    ),
    "gemini": (
        "Point to {target}. The answer should follow the JSON format: "
        '[{{"point": <point>, "label": <label>}}]. The points are in [y, x] format normalized to 0-1000.',
        "point",
        "yx",
        1000,
    ),
    "claude": (  # Claude gives coordinates in the image's pixels (1:1 up to 2576 px since Opus 4.7).
        'Point to {target}. Output its point in JSON as [{{"point": [x, y], "label": "{target}"}}], x the '
        "column and y the row in pixels of this {width}x{height} image.",
        "point",
        "xy",
        None,
    ),
}


def model_args(name: str) -> tuple[str, ...]:
    """The arguments a model names for a skill: a camera and what to point at in its image instead
    of a pixel. The harness then asks the model where that is in that one image (:meth:`Orchestrator.point`)."""
    args = tuple(SKILLS[name].args)
    return POINTED if args == ("camera", "u", "v") else args


def model_forms(name: str) -> tuple[tuple[str, ...], ...]:
    """Each set of arguments a model may name for a skill: :func:`model_args`, and the skill's
    ``or_args`` when it has them (navigate_to: x, y)."""
    return (model_args(name), *((tuple(SKILLS[name].or_args),) if SKILLS[name].or_args else ()))


def point_query(pointer: str, target: str, shape: tuple[int, ...] | None = None) -> str:
    """The grounding query for ``target`` in an image of ``shape`` (height, width, ...); a family that
    points in pixels needs the shape."""
    height, width = shape[:2] if shape is not None else (None, None)
    return POINTERS[pointer][0].format(target=target, width=width, height=height)


def parse_point(text: str, pointer: str, shape: tuple[int, ...]) -> tuple[float, float] | None:
    """The first point in a grounding reply, in pixels (u, v) of an image of ``shape`` (height,
    width, ...); the reply's numbers are on the family's grid (0-1000, or the pixels). None when there
    is no point."""
    _, key, order, grid = POINTERS[pointer]
    try:
        data = json.loads(text[text.find("[") : text.rfind("]") + 1])
        first = data[0][key] if isinstance(data, list) else data[key]
        a, b = float(first[0]), float(first[1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    x, y = (a, b) if order == "xy" else (b, a)
    height, width = shape[:2]
    if grid is not None:
        x, y = x / grid * width, y / grid * height
    return min(max(x, 0.0), width - 1.0), min(max(y, 0.0), height - 1.0)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def prompt_hashes(pointer: str, history: int) -> dict[str, str]:
    """What a model is asked, as hashes, so results of different prompts never pool: ``prompt_sha256``
    covers the system prompt's template, the skill menu, the grounding query of ``pointer``'s family
    and the turn text's form; ``menu_sha256`` the skill menu alone."""
    sample = turn_text(Observation(images={}, pose=(0.0, 0.0, 0.0)), history)
    parts = dict(system=(PROMPTS / "system.md").read_text(), menu=skill_list(), point=POINTERS[pointer][0], turn=sample)
    return dict(prompt_sha256=sha256(json.dumps(parts, sort_keys=True)), menu_sha256=sha256(skill_list()))


def build_system_prompt(brief: str, target_position: tuple[float, float, float] | None) -> str:
    location = (
        "The target's location is unknown."
        if target_position is None
        else f"The target is at world coordinates {[round(v, 3) for v in target_position]}."
    )
    return Template((PROMPTS / "system.md").read_text()).substitute(
        goal=brief,
        skills=skill_list(),
        target_location=location,
    )


def parse_skill_call(text: str) -> SkillCall:
    """The JSON object ``{"skill": ..., "args": {...}}`` in a model reply (fences and prose around it
    are ignored). Raises ``ValueError`` when there is none, the skill is unknown, or the arguments
    do not match the skill's."""
    try:
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        name = str(data["skill"])
        args = dict(data.get("args") or {})
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Could not parse a skill call from {text!r}") from error
    if name not in SKILLS:
        raise ValueError(f"Unknown skill {name!r}; the skills are {sorted(SKILLS)}")
    forms = model_forms(name)
    if not any(sorted(args) == sorted(form) for form in forms):
        expected = " or ".join(map(str, forms))
        raise ValueError(f"{name} expects arguments {expected}, got {tuple(args)}")
    return SkillCall(name, args)


def turn_text(observation: Observation, limit: int) -> str:
    """The text of one turn: the robot's pose when known, the latest results, the reply format."""
    pose = "unknown" if observation.pose is None else [round(v, 3) for v in observation.pose]
    return (
        f"Your pose (x [m], y [m], heading [rad]): {pose}.\n"
        f"Previous skill results:\n{history_text(observation.history, limit)}\n"
        "The camera images follow. Reply with one JSON object."
    )


def history_text(history: list[SkillResult], limit: int) -> str:
    """The last ``limit`` results as lines the model can read."""
    return "\n".join(f"{r.call.name}({r.call.args}) -> {r.status}: {r.reason}" for r in history[-limit:]) or "(none)"


def camera_label(name: str, image) -> str:
    """The line before a camera's image in a turn: its name and size."""
    return f"Camera {name!r}, {image.shape[1]}x{image.shape[0]} px:"


def png_bytes(image) -> bytes:
    """An HxWx3 uint8 image as PNG (lossless): what a model is sent, and what the run's record keeps."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def base64_text(data: bytes) -> str:
    return base64.b64encode(data).decode()


def without_images(value, sent: dict[str, str]):
    """``value`` (a request) with each string of ``sent``'s values (an image as it went into the
    request: base64 or a data URL) replaced by ``<image NAME>``, NAME its key: the request as sent,
    the images kept apart."""
    if isinstance(value, dict):
        return {key: without_images(item, sent) for key, item in value.items()}
    if isinstance(value, list):
        return [without_images(item, sent) for item in value]
    if isinstance(value, str):
        return next((f"<image {name}>" for name, text in sent.items() if value == text), value)
    return value


ORIGINS = {"phygs": "phygs", "foragebench": "harness", "anthropic": "api", "httpx": "api", "requests": "api"}


def origin(error: BaseException) -> str:
    """Where an error came from: the package of the innermost frame that is ours or a client's
    (``phygs``: a PhyGS call refused or failed; ``harness``: ForageBench's code; ``api``: the model's
    client or its server); ``harness`` when none is."""
    frames = traceback.extract_tb(error.__traceback__)
    for frame in reversed(frames):
        for package, name in ORIGINS.items():
            if f"/{package}/" in frame.filename.replace("\\", "/"):
                return name
    return "harness"


class TurnLog:
    """The model's side of a run, kept in the run's recording through ``sink`` (``session.log``; None:
    not kept), the same for every orchestrator:

    - ``model/start``: the episode's system prompt and its hash.
    - ``model/turn``: each turn as it went over the wire: the request (each image a placeholder naming
      it), the raw response, the request id, the model that answered, the retries the client made, the
      seconds, the reply text, its thinking, why it stopped, the token counts; the images as sent (PNG).
    - ``model/point``: each pointing query, the same way; its image is the turn's of that name
      (``image``), or kept with it when it was none of them.
    - ``model/result`` (from :mod:`.loop`): the call the turn's reply named, the call the harness made of
      it (a pixel in the camera's own image), and the status and reason the model is told.
    - ``model/error`` (from :mod:`.loop`): an error, its origin (``model``, ``api``, ``harness``,
      ``phygs``), type, message and traceback.
    """

    def __init__(self, sink=None) -> None:
        self._sink = sink
        self._turn: dict[int, tuple[str, bytes]] = {}  # The current turn's images: id(array) -> (name, PNG).

    def start(self, system_prompt: str) -> None:
        self._write("model/start", dict(system_prompt=system_prompt, sha256=sha256(system_prompt)))

    def encode(self, images: dict) -> dict[str, bytes]:
        """A turn's images as PNG, by camera name; kept so a pointing query on one sends the same bytes."""
        self._turn, pngs = {}, {}
        for name, image in images.items():  # One encoding per array, even under two names.
            pngs[name] = self._turn.setdefault(id(image), (name, png_bytes(image)))[1]
        return pngs

    def encoded(self, image) -> tuple[str | None, bytes]:
        """``image`` as PNG: (its name, the turn's bytes) when it is one of the turn's images, else (None,
        its own bytes)."""
        return self._turn.get(id(image)) or (None, png_bytes(image))

    def turn(self, turn: int, images: dict[str, bytes], **fields) -> None:
        self._write("model/turn", dict(turn=turn, images=sorted(images), **fields), images)

    def point(self, turn: int, name: str | None, png: bytes, **fields) -> None:
        self._write("model/point", dict(turn=turn, image=name, **fields), {} if name else {"image": png})

    def result(self, turn: int, **fields) -> None:
        self._write("model/result", dict(turn=turn, **fields))

    def error(self, turn: int, kind: str, error: BaseException) -> None:
        """``error`` in ``turn``; ``kind`` the origin when known (``model``), else :func:`origin`'s."""
        self._write(
            "model/error",
            dict(
                turn=turn,
                origin=kind or origin(error),
                type=type(error).__name__,
                message=str(error),
                traceback="".join(traceback.format_exception(error)),
            ),
        )

    def _write(self, topic: str, record: dict, images: dict | None = None) -> None:
        if self._sink is not None:
            self._sink(topic, record, images or {})
