# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""A scripted orchestrator: replays a fixed list of skill calls. For tests and smoke runs."""

from __future__ import annotations

from foragebench.agents.model.orchestrator import Observation, Orchestrator, SkillCall


class ScriptedOrchestrator(Orchestrator):
    def __init__(self, calls: list[SkillCall], config=None) -> None:
        super().__init__(config)
        self.calls = list(calls)
        self.seen: list[Observation] = []

    def act(self, observation: Observation) -> SkillCall:
        self.seen.append(observation)
        if not self.calls:
            return SkillCall("done")
        return self.calls.pop(0)
