# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Template agent: one call on every client the spec's tier grants, then finish. Copy this file
and edit run(). Skills (``navigation``, ``manipulation``) walk to a point and stow the arm; the motion
tier adds ``locomotion`` (a body velocity), the joints tier ``arm`` (arm joint angles).

Run it with:
    ./isaaclab.sh -p $FORAGEBENCH/foragebench/eval/run.py --episode dev/grid_table --track privileged \
        --agent template --output <folder>
"""


def run(session):
    print(f"task: {session.task.goal} {session.task.description!r}; grants: {session.grants}")
    packet = session.observe()  # The latest observation the spec allows; time does not pass.
    print("cameras:", sorted(packet.cameras))

    if session.navigation is not None:
        start = packet.localization.pose.matrix[:2, 3].tolist() if packet.localization.valid else None
        print("base at", start)
        feedback = session.wait(session.navigation.navigate_to(-1.0, -0.2, 0.0))  # Simulated time passes in wait.
        print("navigation:", feedback.status, feedback.reason)

    if session.locomotion is not None:  # Motion and joints tiers: body velocity [m/s, m/s, rad/s].
        feedback = session.wait(session.locomotion.command_velocity(0.0, 0.0, 0.3, duration=1.0))
        print("locomotion:", feedback.status)

    if session.arm is not None:  # Joints tier: the first arm joint [m or rad], then back to the start.
        first = session.robot.arm_joints[0]  # The robot's own joint names.
        joints = session.observe().joints  # Needs joint_state in the spec's observations.
        start = float(joints.positions[joints.names.index(first)])
        feedback = session.wait(session.arm.command_joint_positions({first: start + 0.2}))
        print("arm:", feedback.status)
        session.wait(session.arm.command_joint_positions({first: start}))

    for packet in session.stream(seconds=1.0):  # Observations while the robot stands.
        pass

    if "object_targets" in session.grants:  # Privileged, only when granted; every read is logged.
        print("target:", session.hints.target())

    if session.manipulation is not None:
        feedback = session.wait(session.manipulation.stow())  # The task ends with the arm stowed.
        print("stow:", feedback.status, feedback.reason)
    session.finish("template done")
