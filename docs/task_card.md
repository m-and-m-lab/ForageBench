# ForageBench task card (develop, manifest v0)

**Task.** Retrieve: find the object described in words and bring it into the hand with the arm stowed, within a simulated-time budget, in a photorealistic, physically simulated house or test scene, with a Boston Dynamics Spot with Arm (simulated).

**Success.** All four, read from ground truth after the robot has stopped and settled: the target is held (at least 5 cm off where it started, its centre within 0.35 m of the wrist, and every jaw pressing on it), the arm is within 0.05 rad of its stow posture, the base's up axis is within 15° of vertical, and the episode ended by the agent's `finish` or return before the budget. A fall or an emergency stop ends the episode as a failure.

**Also reported.** Reached (the base ends within 1.5 m of the target, or holds it); progress from samples during the run (reached, opened the drawer the target started in, touched, lifted, held), which says where a failed run stopped; SPL and SPL-M (Batra et al. 2020; SPL-M charges each manipulation 1 m of path on both the optimal and the actual side) for episodes with a stated optimal path; skill execution success; path length; simulated time. No difficulty tiers yet.

**Conduct, reported beside the outcome.** Unintended arm contacts at or above 0.5 N (the squeeze on a grasped body excluded), with the peak force; drawers the agent opened and left more than 3 cm open; other objects moved more than 5 cm. `clean` means none.

**Tracks.** `privileged` (true pose, known map, target position, drawer handles), `gt_localization` (true pose only), `onboard` (planned: nothing). Every privileged read is audited.

**Budgets.** Simulated seconds per episode (420 for the grid episodes, 600 for the house). The clock is `charged`: time passes only while the agent waits on the robot, so thinking is free. Wall time and tool calls are recorded, not limited.

**Episodes.** Manifest v0: three development episodes on two scenes. They are for developing agents, not for claims about unseen houses. Manifest v1 (25 scenes, 100 episodes, hidden test split) is not released.

**Physics.** PhysX at 250 Hz, PhyGS 0.7.0. No attached grasps; drawers are prismatic joints; the base walks under a learned policy; contacts are measured, not prevented. Validated scene releases: `bear_loop_house` 1.1.0 (240 and 500 Hz settling and joint checks). Photorealism is not measured.

**What is not claimed.** That success on the dev episodes transfers to unseen houses; that the oracle's success rate is attainable by a method without privileged information; that the rendered appearance matches the physical validation; anything about the real robot.

**Provenance in every result.** PhyGS version and commit, ForageBench commit, dirty flags, the rules file, track file, episode file and thresholds hashes, the scene USD's hash and release, the robot USD and policy hashes, the effective backends.
