# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Copy the benchmark-side files from the lab's internal interactive-search tree into this checkout.

Only two things flow from there: the retrieve evaluator (written and scored first in that tree) and
the example agents. Everything else in ForageBench is its own. The script rewrites the import
names and never writes to interactive-search; review ``git diff`` afterwards.

    python3 tools/sync_from_interactive_search.py --source ../interactive-search [--dry_run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = [
    ("src/interactive_search/tasks/retrieve.py", "foragebench/tasks/retrieve/evaluator.py"),
    ("src/interactive_search/tasks/retrieve.yaml", "foragebench/tasks/retrieve/thresholds.yaml"),
    ("src/interactive_search/agents/template.py", "foragebench/agents/template.py"),
]
RULES = [
    (
        r'THRESHOLDS = Path\(__file__\)\.with_name\("retrieve\.yaml"\)',
        'THRESHOLDS = Path(__file__).with_name("thresholds.yaml")',
    ),
    (r"interactive_search\.tasks\.load_task", "foragebench.tasks.load_task"),
    (r"interactive_search", "phygs"),
    (r"scripts/interactive-search", "$FORAGEBENCH"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dry_run", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    for src, dst in MAPPING:
        text = (source / src).read_text()
        for pattern, repl in RULES:
            text = re.sub(pattern, repl, text)
        if args.dry_run:
            print(f"{src} -> {dst}")
        else:
            (ROOT / dst).write_text(text)
    print(f"{'would copy' if args.dry_run else 'copied'} {len(MAPPING)} files")


if __name__ == "__main__":
    main()
