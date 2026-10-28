# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The null agent: observes once and finishes. The benchmark's floor and its smoke test."""


def run(session):
    packet = session.observe()
    print(f"null agent: task {session.task.goal} {session.task.description!r}; cameras {sorted(packet.cameras)}")
    session.finish("null agent: nothing attempted")
