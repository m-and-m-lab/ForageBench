# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Run a set of episodes, each in its own simulator process, and summarize the results.

    ./isaaclab.sh -p -m foragebench suite --set dev --track privileged --agent oracle \\
        --repeats 3 --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_dev_oracle

Every run is ``foragebench run`` with the same arguments; its folder and log land under ``--output``. The
summary (``summary.json`` and a table) comes from :mod:`foragebench.eval.results`. A run that breaks
or fails its start check is listed apart from the rates and does not stop the suite.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from foragebench.episodes import manifest_entries
from foragebench.eval import results

ROOT = Path(__file__).resolve().parents[2]  # The ForageBench checkout (installed editable).


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", default="dev", help="A set of the manifest")
    parser.add_argument("--track", default="privileged")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--repeats", type=int, default=1, help="Runs per episode (seeds 0..repeats-1)")
    parser.add_argument("--only", nargs="*", default=None, help="Episode ids of the set to run")
    parser.add_argument("--benchmark", type=Path, default=ROOT / "configs" / "benchmark_v1.yaml")
    parser.add_argument("--output", type=Path, required=True, help="A fresh folder for the suite")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()
    rules = yaml.safe_load(args.benchmark.read_text())
    entries = manifest_entries(ROOT / rules["manifest"])
    episodes = [key for key, (set_name, _) in entries.items() if set_name == args.set]
    if args.only:
        episodes = [key for key in episodes if key.split("/", 1)[1] in args.only]
    if not episodes:
        parser.error(f"No episodes in set {args.set!r}; the manifest has {sorted(entries)}")
    args.output.mkdir(parents=True, exist_ok=False)
    for key in episodes:
        for seed in range(args.repeats):
            label = f"{key.replace('/', '_')}_s{seed}"
            folder = args.output / label
            command = [
                sys.executable,
                "-m",
                "foragebench",
                "run",
                "--episode",
                key,
                "--track",
                args.track,
                "--agent",
                args.agent,
                "--seed",
                str(seed),
                "--benchmark",
                str(args.benchmark),
                "--output",
                str(folder),
                *(["--record"] if args.record else []),
                *(["--headless"] if args.headless else []),
            ]
            print(f"== {label}", flush=True)
            with (args.output / f"{label}.log").open("w") as log:
                code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
            path = folder / "result.json"
            status = json.loads(path.read_text()).get("status", "completed") if path.exists() else "error"
            print(f"   {status} (exit {code})", flush=True)
    summary = results.summarize(args.output, rules.get("spl_m_cost_per_manipulation_m", 1.0))
    (args.output / "summary.json").write_text(results.dumps(summary))
    print(results.table(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
