# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The ``foragebench`` command: one name for the benchmark's entry points.

    foragebench describe --episode dev/grid_table --track privileged --agent oracle   # No simulator.
    foragebench run --episode dev/grid_table --track privileged --agent oracle --output <folder> [--record]
    foragebench suite --set dev --track privileged --agent oracle --repeats 5 --output <folder>
    foragebench results <folder>                     # The table and summary.json of finished runs.
    foragebench scenes list | fetch                  # The scene releases the episodes need.
    foragebench version                              # ForageBench, and PhyGS pinned and installed.

Run it with Isaac Lab's Python: ``./isaaclab.sh -p -m foragebench <command>``. Each subcommand runs its
module with the remaining arguments, so ``foragebench run --help`` is the run's own help.
"""

from __future__ import annotations

import runpy
import sys

# Commands whose module runs as a script (it parses the arguments and starts Isaac Sim at import).
SCRIPTS = {"run": "foragebench.eval.run", "suite": "foragebench.eval.suite"}
# Commands with a main(argv) function, imported only when called.
MAINS = {
    "describe": "foragebench.eval.describe",
    "results": "foragebench.eval.results",
    "scenes": "foragebench.scenes",
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if args else 2
    command, rest = args[0], args[1:]
    if command == "version":
        from pathlib import Path

        import yaml

        import foragebench

        rules = Path(__file__).resolve().parents[1] / "configs" / "benchmark_v1.yaml"
        pinned = yaml.safe_load(rules.read_text())["phygs_version"]
        print(f"foragebench {foragebench.__version__}; PhyGS pinned {pinned}, installed {foragebench.phygs_version()}")
        return 0
    if command in SCRIPTS:
        sys.argv = [f"foragebench {command}", *rest]
        runpy.run_module(SCRIPTS[command], run_name="__main__", alter_sys=True)
        return 0
    if command in MAINS:
        import importlib

        return int(importlib.import_module(MAINS[command]).main(rest) or 0)
    print(f"foragebench: unknown command {command!r}\n\n{__doc__.strip()}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
