"""The leaderboard: the published results in one file, ``leaderboard/results.json``, and the README's
table written from it.

    foragebench leaderboard add <suite folder>    # Score a suite's runs into the file.
    foragebench leaderboard readme [--check]      # Write the README's table; --check: exit 1 if it is stale.

An entry is one group of :func:`results.summarize`, one (track, agent, model, prompt) on one episode
set: n (the completed runs), the successes, their rate and its Wilson 95% interval, the per-episode
results, the reached and clean rates, the runs that could not be scored, the PhyGS and rules versions,
the date of the runs and their folder. ``add`` replaces the entry of the same group, and refuses
unpinned runs (another PhyGS version or commit than the rules pin, or a dirty checkout), naming why.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from foragebench.eval import results

RESULTS = results.ROOT / "leaderboard" / "results.json"
README = results.ROOT / "README.md"
RULES = results.ROOT / "configs" / "benchmark_v1.yaml"
BEGIN = "<!-- leaderboard: written by `foragebench leaderboard readme` from leaderboard/results.json -->"
END = "<!-- /leaderboard -->"
KEY = ("benchmark", "set", "track", "agent", "model", "prompt_sha256")
STAMP = re.compile(r"(\d{4})(\d{2})(\d{2})-\d{4}")


def date_of(folder: Path) -> str:
    """The date in the run folder's name (``output_check/<YYYYMMDD-HHMM>_<label>``), as YYYY-MM-DD."""
    for part in reversed(folder.resolve().parts):
        found = STAMP.match(part)
        if found:
            return "-".join(found.groups())
    raise ValueError(f"{folder}: no <YYYYMMDD-HHMM> folder in the path; pass --date.")


def where(folder: Path) -> str:
    """The suite's folder as stored: from ``output_check/`` on, else its name (never a machine's path)."""
    parts = folder.resolve().parts
    if "output_check" in parts:
        return "/".join(parts[parts.index("output_check") :])
    return folder.name


def entries(folder: Path, rules: dict, date: str | None = None) -> list[dict]:
    """The leaderboard entries of a suite's folder, one per group of its completed runs."""
    summary = results.summarize(folder, rules.get("spl_m_cost_per_manipulation_m", 1.0), rules)
    every, missing = results.load_results(folder)
    scored = [r for r in every if r["status"] == "completed"]
    if not scored:
        raise ValueError(f"{folder}: no completed run to score.")
    sets = {(r.get("benchmark"), r.get("set")) for r in scored}
    if len(sets) != 1:
        raise ValueError(f"{folder}: one benchmark and episode set per folder, found {sorted(sets, key=str)}.")
    ((benchmark, episode_set),) = sets
    unscored = not_scored(folder, summary["groups"], every, missing)
    unpinned = [(r, results.pin_reasons(r, rules)) for r in scored]
    if any(reasons for _, reasons in unpinned):
        bad = [(r, reasons) for r, reasons in unpinned if reasons]
        groups = ", ".join(sorted({f"{r['agent']} on {r['track']}" for r, _ in bad}))
        found = "; ".join(sorted({reason for _, reasons in bad for reason in reasons}))
        count = f"{len(bad)} of {len(scored)} runs ({groups})"
        raise ValueError(f"{folder}: {count} are unpinned: {found}. Do not publish them.")
    out = []
    for group in summary["groups"]:
        name = f"{group['agent']} on {group['track']}"
        if group["phygs_versions"] != [rules["phygs_version"]]:
            raise ValueError(
                f"{folder}: the runs of {name} used PhyGS {group['phygs_versions']}; the rules pin"
                f" {rules['phygs_version']}."
            )
        low, high = group["success_ci95"]
        skills = group["skill_execution_success"]
        out.append(
            dict(
                benchmark=benchmark,
                set=episode_set,
                track=group["track"],
                agent=group["agent"],
                model=group["model"],
                prompt_sha256=group["prompt_sha256"],
                n=group["runs"],
                successes=group["successes"],
                success_rate=round(group["success_rate"], 4),
                success_ci95=[round(low, 4), round(high, 4)],
                reached_rate=round(group["reached_rate"], 4),
                clean_successes=group["clean_successes"],
                clean_rate=round(group["clean_rate"], 4),
                skill_execution_success=None if skills is None else round(skills, 4),
                mean_sim_seconds=round(group["mean_sim_seconds"], 1),
                episodes=group["episodes"],
                not_scored=unscored[key_of(group)],
                phygs_version=group["phygs_versions"][0],
                rules_version=summary["rules_version"],
                date=date or date_of(folder),
                runs=where(folder),
            )
        )
    return out


def key_of(group: dict) -> tuple:
    return (group["track"], group["agent"], group["model"], group["prompt_sha256"])


def not_scored(folder: Path, groups: list[dict], every: list[dict], missing: list[str]) -> dict[tuple, list[dict]]:
    """The runs that could not be scored, by group. A run without its agent's setup (``run.py`` writes none
    when the World broke) belongs to the one group of its track and agent; a run folder without a result
    belongs to the folder's one group. A run that cannot be placed is an error, never dropped."""
    out = {key_of(group): [] for group in groups}
    for r in every:
        if r["status"] == "completed":
            continue
        key = (r.get("track"), r.get("agent"), *results.setup_of(r))
        if key not in out:
            loose = [k for k in out if k[:2] == key[:2]]
            if len(loose) != 1 or key[2:] != (None, None):
                raise ValueError(
                    f"{folder}: cannot tell which agent's entry run {r['run']} ({r['status']}) belongs to."
                )
            key = loose[0]
        out[key].append(dict(run=r["run"], status=r["status"], reason=r.get("reason")))
    if missing:
        if len(out) != 1:
            raise ValueError(f"{folder}: run folders without a result.json ({missing}) and several agents' entries.")
        (key,) = out
        out[key] += [dict(run=run, status="error", reason="no result.json") for run in missing]
    return out


def add(board: dict, new: list[dict]) -> dict:
    """The board with ``new`` in place of the entries of the same groups."""
    keys = {tuple(entry[k] for k in KEY) for entry in new}
    kept = [entry for entry in board.get("entries", []) if tuple(entry[k] for k in KEY) not in keys]
    ordered = sorted(kept + new, key=lambda e: (e["benchmark"], e["set"], e["track"], -e["success_rate"], e["agent"]))
    return dict(board, entries=ordered)


def table(board: dict) -> str:
    """The README's Markdown table of the board."""
    head = ("Agent", "Track", "Set", "n", "Success", "Wilson 95%", "Clean successes", "Per episode (successes/runs)")
    head += ("PhyGS", "Rules", "Date")
    lines = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for e in board["entries"]:
        agent = e["agent"] + (f" ({e['model']})" if e.get("model") else "")
        n = f"{e['n']}" + (f" (+{len(e['not_scored'])} not scored)" if e["not_scored"] else "")
        low, high = e["success_ci95"]
        episodes = ", ".join(f"`{name}` {r['successes']}/{r['runs']}" for name, r in e["episodes"].items())
        cells = (agent, f"`{e['track']}`", e["set"], n, f"{e['successes']}/{e['n']}", f"{low:.2f}–{high:.2f}")
        cells += (f"{e['clean_successes']}/{e['n']}", episodes, e["phygs_version"], e["rules_version"], e["date"])
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(lines)


def written(readme: str, board: dict) -> str:
    """The README with the table between its markers replaced by the board's."""
    start = readme.find(BEGIN)
    end = readme.find(END, start + len(BEGIN)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise ValueError(f"The README has no leaderboard markers ({BEGIN} ... {END}).")
    return readme[: start + len(BEGIN)] + "\n" + table(board) + "\n" + readme[end:]


def main(argv: list[str] | None = None) -> int:
    """``foragebench leaderboard add <folder>`` or ``foragebench leaderboard readme [--check]``."""
    parser = argparse.ArgumentParser(description="The leaderboard: leaderboard/results.json and the README's table.")
    commands = parser.add_subparsers(dest="command", required=True)
    adding = commands.add_parser("add", help="Score a suite's runs into the results file")
    adding.add_argument("folder", type=Path, help="A suite's folder (foragebench suite --output)")
    adding.add_argument("--date", default=None, help="The runs' date, YYYY-MM-DD (default: from the folder name)")
    adding.add_argument("--benchmark", type=Path, default=RULES)
    readme = commands.add_parser("readme", help="Write the README's table from the results file")
    readme.add_argument("--check", action="store_true", help="Exit 1 if the README's table is not the file's")
    for sub in (adding, readme):
        sub.add_argument("--results", type=Path, default=RESULTS)
    readme.add_argument("--readme", type=Path, default=README)
    args = parser.parse_args(argv)
    board = json.loads(args.results.read_text()) if args.results.is_file() else {"entries": []}
    if args.command == "add":
        new = entries(args.folder, yaml.safe_load(args.benchmark.read_text()), args.date)
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(json.dumps(add(board, new), indent=1) + "\n")
        print(table(dict(entries=new)))
        return 0
    text = args.readme.read_text()
    updated = written(text, board)
    if args.check:
        if updated != text:
            print(f"{args.readme}: the leaderboard table is stale; run `foragebench leaderboard readme`.")
            return 1
        return 0
    args.readme.write_text(updated)
    return 0
