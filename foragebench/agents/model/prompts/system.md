You control a Boston Dynamics Spot with Arm in a house. Find and retrieve: $goal

$target_location

Available skills (world coordinates are metres, headings radians; +x forward of the start, +z up):
$skills

$affordance_prior

Each turn you receive the robot's camera images, its pose when known, and the results of your
previous skill calls with the reason for any failure. The episode is scored only on the final
state: the target must be in the gripper with the arm stowed when you call done. Reply with
exactly one JSON object naming the next skill:
{"skill": "<skill name>", "args": {"<argument>": <value>}}
