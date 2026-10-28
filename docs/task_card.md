# ForageBench task card (develop, manifest v0)

**Task.** Retrieve: find the object described in words and bring it into the hand with the arm stowed, within a simulated-time budget, in a photorealistic, physically simulated house or test scene, with a Boston Dynamics Spot with Arm (simulated).

**Success.** All four, read from ground truth once after the robot has stopped and settled: the target is held (at least 5 cm off where it started and its centre within 0.35 m of the wrist), the arm is within 0.05 rad of its stow posture, the base's up axis is within 15° of vertical, and the episode ended by the agent's `finish` or return before the budget. A fall or an emergency stop ends the episode as a failure.

**Conduct, reported beside the outcome.** Unintended arm contacts at or above 0.5 N (the squeeze on a grasped body excluded), with the peak force; drawers the agent opened and left more than 3 cm open. `clean` means none.

**Tracks.** `privileged` (true pose, known map, target position, drawer handles), `gt_localization` (true pose only), `onboard` (planned: nothing). Every privileged read is audited.

**Budgets.** Simulated seconds per episode (420 for the grid episodes, 600 for the house). The clock is `charged`: time passes only while the agent waits on the robot, so thinking is free. Wall time and tool calls are recorded, not limited.

**Episodes.** Manifest v0: three development episodes on two scenes. They are for developing agents, not for claims about unseen houses. Manifest v1 (25 scenes, 100 episodes, hidden test split) is not released.

**Physics.** PhysX at 250 Hz, PhyGS 0.3.0. No attached grasps; drawers are prismatic joints; the base walks under a learned policy; contacts are measured, not prevented. Validated scene releases: `bear_loop_house` 1.1.0 (240 and 500 Hz settling and joint checks). Photorealism is not measured.

**What is not claimed.** That success on the dev episodes transfers to unseen houses; that the oracle's success rate is attainable by a method without privileged information; that the rendered appearance matches the physical validation; anything about the real robot.

**Provenance in every result.** PhyGS version and commit, ForageBench commit, dirty flags, the rules file, track file, episode file and thresholds hashes, the scene USD's hash and release, the robot USD and policy hashes, the effective backends.
