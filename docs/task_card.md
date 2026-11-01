# ForageBench task card (develop, manifest v0)

**The question v1 answers.** Given reliable walking, picking and drawer skills, can a model find and retrieve the requested object in a home it has not seen, and when it fails, is it because of where it searched, what it chose, or what it pointed at?

**Task.** Retrieve: find the object described in words and bring it into the hand with the arm stowed, within a simulated-time budget, in a photorealistic, physically simulated house or test scene, with a Boston Dynamics Spot with Arm (simulated).

**Success.** All four, read from ground truth after the robot has stopped and settled: the target is held (at least 5 cm off where it started, its centre within 0.35 m of the wrist, and every jaw pressing on it), the arm is within 0.05 rad of its stow posture, the base's up axis is within 15° of vertical, and the episode ended by the agent's `finish` or return before the budget. A fall or an emergency stop ends the episode as a failure.

**Also reported.** Reached (the base ends within 1.5 m of the target, or holds it); progress from samples during the run (reached, opened the drawer the target started in, touched, lifted, held), which says where a failed run stopped; SPL and SPL-M (Batra et al. 2020; SPL-M charges each manipulation 1 m of path on both the optimal and the actual side) for episodes with a stated optimal path; skill execution success; path length; simulated time. No difficulty tiers yet.

**Conduct, reported beside the outcome.** Unintended arm contacts at or above 0.5 N (the squeeze on a grasped body excluded), with the peak force; drawers the agent opened and left more than 3 cm open; other objects moved more than 5 cm. `clean` means none.

**The skills and their ceilings.** One primary measurement: the success of a model that chooses PhyGS's skills under their own names (navigate_to, explore, look_at, open_drawer, close_drawer, pick, stow) and points at what they act on; a harness-side estimator (`foragebench/agents/model/perception.py`) turns each point into the affordance the skill takes. Its ceilings are measured beside it: the `oracle` (the skills on the true affordances: the motion ceiling), the `pointing_oracle` (the skills with perfect points through the estimator: the estimator's ceiling), and the noise floor (the oracle repeated). A failure is attributed to a wrong choice, a wrong point, a wrong estimate or a failed motion (planned: the attribution is read from the run's logs, not computed yet). The model's menu and prompt are versioned with the harness. Not in v1: separate affordance or trajectory tracks, doors.

**Tracks.** `privileged` (true pose, known map, target position, drawer handles), `gt_localization` (true pose only), `onboard` (planned: nothing). Every privileged read is audited.

**Budgets.** Simulated seconds per episode (420 for the grid episodes, 600 for the house). The clock is `charged`: time passes only while the agent waits on the robot, so thinking is free. Wall time and tool calls are recorded, not limited.

**Episodes.** Manifest v0: three development episodes on two scenes. They are for developing agents, not for claims about unseen houses. Manifest v1 (25 scenes, 100 episodes, hidden test split) is not released.

**Physics.** PhysX at 250 Hz, PhyGS 0.10.0. No attached grasps; drawers are prismatic joints; the base walks under a learned policy; contacts are measured, not prevented. Validated scene releases: `bear_loop_house` 1.1.0 (240 and 500 Hz settling and joint checks). Photorealism is not measured.

**What is not claimed.** That success on the dev episodes transfers to unseen houses; that the oracle's success rate is attainable by a method without privileged information; that the rendered appearance matches the physical validation; anything about the real robot.

**Provenance in every result.** PhyGS version and commit, ForageBench commit, dirty flags, the rules file, track file, episode file and thresholds hashes, the scene USD's hash and release, the robot USD and policy hashes, the effective backends.
