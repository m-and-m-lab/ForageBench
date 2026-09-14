"""High-level skill API matched to the Boston Dynamics Spot with Arm SDK.

Using this API is optional: the benchmark also exposes continuous control of the robot.
"""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class SkillName(StrEnum):
    NAVIGATE = "navigate"
    PLACE = "place"
    OPEN_DOOR = "open_door"
    CLOSE_DOOR = "close_door"
    OPEN_DRAWER = "open_drawer"
    CLOSE_DRAWER = "close_drawer"
    REPORT_FOUND = "report_found"


SKILL_ARGS: dict[SkillName, tuple[str, ...]] = {
    SkillName.NAVIGATE: ("target",),
    SkillName.PLACE: ("receptacle",),
    SkillName.OPEN_DOOR: ("reference",),
    SkillName.CLOSE_DOOR: ("reference",),
    SkillName.OPEN_DRAWER: ("reference",),
    SkillName.CLOSE_DRAWER: ("reference",),
    SkillName.REPORT_FOUND: ("object",),
}


class SkillStatus(StrEnum):
    SUCCESS = "success"
    INCOMPATIBLE = "incompatible"
    """The skill cannot apply to its argument. Terminates the episode."""
    FAILED = "failed"
    # TODO: split FAILED into the specific failure modes reported by the PhyGS HAL.


@dataclass(frozen=True)
class SkillCall:
    name: SkillName
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillResult:
    call: SkillCall
    status: SkillStatus
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SkillStatus.SUCCESS


class SkillAPI(Protocol):
    def execute(self, call: SkillCall) -> SkillResult: ...

    def execute_async(self, call: SkillCall) -> Future[SkillResult]: ...
