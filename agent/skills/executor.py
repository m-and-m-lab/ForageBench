"""Dispatches skill calls to the baseline skill implementations."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from agent.interface.skills import SkillCall, SkillName, SkillResult, SkillStatus
from agent.skills.articulation import close_door, close_drawer, open_door, open_drawer
from agent.skills.manipulation import place, report_found
from agent.skills.navigation import navigate

SKILLS: dict[SkillName, Callable[..., SkillStatus]] = {
    SkillName.NAVIGATE: navigate,
    SkillName.PLACE: place,
    SkillName.OPEN_DOOR: open_door,
    SkillName.CLOSE_DOOR: close_door,
    SkillName.OPEN_DRAWER: open_drawer,
    SkillName.CLOSE_DRAWER: close_drawer,
    SkillName.REPORT_FOUND: report_found,
}


class BaselineSkillAPI:
    """`SkillAPI` backed by the baseline skills.

    `robot` is the PhyGS Spot hardware-abstraction handle.
    """

    def __init__(self, robot: Any):
        self._robot = robot
        # A single robot executes one skill at a time.
        self._pool = ThreadPoolExecutor(max_workers=1)

    def execute(self, call: SkillCall) -> SkillResult:
        status = SKILLS[call.name](self._robot, **call.args)
        return SkillResult(call, status)

    def execute_async(self, call: SkillCall) -> Future[SkillResult]:
        return self._pool.submit(self.execute, call)
