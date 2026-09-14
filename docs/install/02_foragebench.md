# 2. Install ForageBench

Run these commands **inside the IsaacLab container**. IsaacLab's Python is invoked through
`isaaclab.sh -p`.

## Clone with submodules

ForageBench uses git submodules for [AO-Grasp + Contact-GraspNet](https://github.com/m-and-m-lab/ao-grasp)
and [cuRobo](https://github.com/m-and-m-lab/curobo), checked out under `third_party/`.

```bash
git clone --recursive https://github.com/m-and-m-lab/ForageBench.git
cd ForageBench
# Or, on an existing checkout:
git submodule update --init --recursive
```

## Python dependencies

```bash
ISAACLAB=/workspace/isaaclab/isaaclab.sh

# ForageBench dependencies, plus the extras for the orchestrators you plan to run
$ISAACLAB -p -m pip install -e ".[gemini,qwen]"

# cuRobo
$ISAACLAB -p -m pip install -e third_party/curobo --no-build-isolation

# AO-Grasp + Contact-GraspNet
# TODO: document install steps and checkpoint downloads
```

## API keys

The Gemini Robotics ER orchestrator reads `GEMINI_API_KEY` from the environment:

```bash
export GEMINI_API_KEY=...
```

## Verify

```bash
$ISAACLAB -p -m pytest
```
