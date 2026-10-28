# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Results: read ``result.json`` files and summarize them (success and clean rates with confidence intervals).

The success rate is the fraction of completed runs whose outcome is ``success``; the clean rate the
fraction of successes with no conduct finding. Intervals are Wilson 95% intervals. Runs that broke
(no ``result.json``) are counted as errors and are not in the rates: a benchmark result reports them.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def unpinned(result: dict) -> bool:
    """Whether the run came from a dirty checkout of PhyGS (``code``) or ForageBench."""
    provenance = result.get("provenance", {})
    return any(bool((provenance.get(key) or {}).get("dirty")) for key in ("code", "foragebench"))


def load_results(folder: Path) -> tuple[list[dict], list[str]]:
    """(results, names of run folders without a result)."""
    results, errors = [], []
    for run in sorted(p for p in folder.iterdir() if p.is_dir()):
        path = run / "result.json"
        if path.is_file():
            results.append(json.loads(path.read_text()))
        else:
            errors.append(run.name)
    return results, errors


def summarize(folder: Path) -> dict:
    """Rates per (track, agent) and per episode, from the runs under ``folder``."""
    results, errors = load_results(Path(folder))
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for result in results:
        groups[(result["track"], result["agent"])].append(result)
    out = dict(runs=len(results), errors=errors, groups=[])
    for (track, agent), items in sorted(groups.items()):
        successes = [r for r in items if r["outcome"] == "success"]
        clean = [r for r in successes if r.get("clean")]
        episodes = {}
        for episode in sorted({r["episode"] for r in items}):
            mine = [r for r in items if r["episode"] == episode]
            won = sum(r["outcome"] == "success" for r in mine)
            episodes[episode] = dict(runs=len(mine), successes=won, success_rate=won / len(mine))
        out["groups"].append(
            dict(
                track=track,
                agent=agent,
                runs=len(items),
                successes=len(successes),
                success_rate=len(successes) / len(items),
                success_ci95=wilson(len(successes), len(items)),
                clean_successes=len(clean),
                clean_rate=len(clean) / len(items),
                mean_sim_seconds=sum(r["sim_seconds"] for r in items) / len(items),
                episodes=episodes,
                phygs_versions=sorted({r["provenance"].get("phygs_version", "?") for r in items}),
                unpinned=sum(unpinned(r) for r in items),  # Runs from a dirty PhyGS or ForageBench checkout.
            )
        )
    return out


def dumps(summary: dict) -> str:
    return json.dumps(summary, indent=1)


def table(summary: dict) -> str:
    """A plain-text table of the summary."""
    head = ("track", "agent", "runs", "success", "95% CI", "clean", "sim s", "unpinned")
    lines = [
        f"{head[0]:<16} {head[1]:<12} {head[2]:>4} {head[3]:>8} {head[4]:>14} {head[5]:>6} {head[6]:>7} {head[7]:>8}"
    ]
    for g in summary["groups"]:
        low, high = g["success_ci95"]
        lines.append(
            f"{g['track']:<16} {g['agent']:<12} {g['runs']:>4} {g['success_rate']:>8.2f}"
            f" {low:>6.2f}-{high:<7.2f} {g['clean_rate']:>6.2f} {g['mean_sim_seconds']:>7.1f} {g['unpinned']:>8}"
        )
    if summary["errors"]:
        lines.append(f"errors (no result): {', '.join(summary['errors'])}")
    return "\n".join(lines)
