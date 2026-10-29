# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Results: read ``result.json`` files and summarize them.

Success rate (outcome ``success``), clean rate (successes with no conduct finding), Wilson 95%
intervals; SPL and SPL-M (Batra et al. 2020; SPL-M charges each manipulation a path cost) over the
runs whose episode states an optimal path length, else not reported (``None``); skill execution
success (skill calls that ended ``succeeded``). Runs that broke (no ``result.json``) are counted as
errors and are not in the rates: a benchmark result reports them.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path


def spl(successes: list[bool], optimal: list[float], actual: list[float]) -> float | None:
    """Success weighted by path length: mean of S_i * l_i / max(p_i, l_i); None without runs."""
    if not (len(successes) == len(optimal) == len(actual)):
        raise ValueError("successes, optimal and actual must have the same length")
    if not successes:
        return None
    terms = [s * (o / max(a, o) if max(a, o) > 0 else 1.0) for s, o, a in zip(successes, optimal, actual)]
    return sum(terms) / len(terms)


def spl_m(results: list[dict], cost_per_manipulation_m: float) -> float | None:
    """SPL with each manipulation charged ``cost_per_manipulation_m`` [m] on both paths."""
    rated = [
        r for r in results if r.get("optimal_path_length_m") is not None and r.get("optimal_manipulations") is not None
    ]
    cost = cost_per_manipulation_m
    return spl(
        [r["outcome"] == "success" for r in rated],
        [r["optimal_path_length_m"] + cost * r["optimal_manipulations"] for r in rated],
        [r["path_length_m"] + cost * r["manipulations"] for r in rated],
    )


def skill_execution_success(results: list[dict]) -> float | None:
    """The fraction of skill calls, pooled over runs, that ended succeeded; None without calls."""
    calls = sum(r.get("skill_calls", 0) for r in results)
    return sum(r.get("skill_successes", 0) for r in results) / calls if calls else None


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


def summarize(folder: Path, cost_per_manipulation_m: float = 1.0) -> dict:
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
        rated = [r for r in items if r.get("optimal_path_length_m") is not None]
        out["groups"].append(
            dict(
                track=track,
                agent=agent,
                runs=len(items),
                successes=len(successes),
                success_rate=len(successes) / len(items),
                success_ci95=wilson(len(successes), len(items)),
                spl=spl(
                    [r["outcome"] == "success" for r in rated],
                    [r["optimal_path_length_m"] for r in rated],
                    [r["path_length_m"] for r in rated],
                ),
                spl_m=spl_m(items, cost_per_manipulation_m),
                spl_runs=len(rated),
                skill_execution_success=skill_execution_success(items),
                mean_path_length_m=sum(r.get("path_length_m", 0.0) for r in items) / len(items),
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
    head = ("track", "agent", "runs", "success", "95% CI", "clean", "SPL", "skills", "path m", "sim s", "unpinned")
    lines = [
        f"{head[0]:<16} {head[1]:<10} {head[2]:>4} {head[3]:>8} {head[4]:>12} {head[5]:>6} {head[6]:>5}"
        f" {head[7]:>6} {head[8]:>6} {head[9]:>6} {head[10]:>8}"
    ]
    for g in summary["groups"]:
        low, high = g["success_ci95"]
        spl_text = "-" if g["spl"] is None else f"{g['spl']:.2f}"
        skills = "-" if g["skill_execution_success"] is None else f"{g['skill_execution_success']:.2f}"
        lines.append(
            f"{g['track']:<16} {g['agent']:<10} {g['runs']:>4} {g['success_rate']:>8.2f}"
            f" {low:>5.2f}-{high:<6.2f} {g['clean_rate']:>6.2f} {spl_text:>5} {skills:>6}"
            f" {g['mean_path_length_m']:>6.1f} {g['mean_sim_seconds']:>6.0f} {g['unpinned']:>8}"
        )
    if summary["errors"]:
        lines.append(f"errors (no result): {', '.join(summary['errors'])}")
    return "\n".join(lines)
