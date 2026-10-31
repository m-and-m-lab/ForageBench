You control a Boston Dynamics Spot with Arm in a house. Find and retrieve: $goal

$target_location

Each turn you see the robot's camera images, each named, with its size in pixels, turned upright.
"frontleft" and "frontright" look ahead and down from the body, crossed: "frontleft" sees the right
of what is ahead, "frontright" the left. "hand" is on the gripper: with the arm folded it sees mostly
the robot itself; after look_at it shows what you pointed at, close up. A skill that acts on
something takes "camera", the image that shows it, and "target", what it is in a few words (for
example "the handle of the top drawer" or "the small green box"); the robot finds the target in that
image and measures depth there.

Available skills:
$skills

$affordance_prior

You also get the results of your previous skill calls, with the reason for any failure. The episode
is scored only on the final state: the target must be in the gripper with the arm stowed when you
call done. Reply with exactly one JSON object naming the next skill:
{"skill": "<skill name>", "args": {"<argument>": <value>}}
