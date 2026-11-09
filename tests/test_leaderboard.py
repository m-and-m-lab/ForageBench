"""The leaderboard: entries scored from a suite's runs, and the README's table written from the results file."""

from __future__ import annotations

import json
import re

import pytest

from foragebench.eval import leaderboard

TAG = "67fddf15b94f7b99e82be2257b89d83fefdcb4ac"  # PhyGS v0.12.0's commit.
RULES = {"phygs_version": "0.12.0", "phygs_commit": TAG, "spl_m_cost_per_manipulation_m": 1.0}
LATER = "47e3edc" + "0" * 33  # A later PhyGS commit whose __version__ still says 0.12.0.


def result(
    episode: str,
    outcome: str = "success",
    dirty: bool = False,
    phygs: str = "0.12.0",
    commit: str | None = TAG,
    unpinned: list[str] | None = None,
    **over,
) -> dict:
    provenance = {
        "phygs_version": phygs,
        "code": {"commit": commit, "dirty": dirty},
        "foragebench": {"dirty": False},
    }
    if unpinned is not None:  # Runs write why they are unpinned; older results have no such key.
        provenance["unpinned"] = unpinned
    return (
        dict(
            benchmark="v1",
            set="dev",
            track="privileged",
            agent="oracle",
            episode=episode,
            status="completed",
            outcome=outcome,
            clean=outcome == "success",
            reached=True,
            progress={},
            path_length_m=3.0,
            manipulations=2,
            skill_calls=2,
            skill_successes=2,
            sim_seconds=60.0,
            rules={"version": 3},
            provenance=provenance,
        )
        | over
    )


def suite(folder, runs: dict) -> None:
    for name, record in runs.items():
        (folder / name).mkdir(parents=True)
        if record is not None:
            (folder / name / "result.json").write_text(json.dumps(record))


def test_an_entry_has_n_the_wilson_interval_and_the_per_episode_results(tmp_path):
    folder = tmp_path / "output_check" / "20261108-1530_dev_oracle"
    suite(folder, {"a": result("grid_table"), "b": result("grid_table", "failure"), "c": result("grid_drawer")})
    (entry,) = leaderboard.entries(folder, RULES)
    assert (entry["n"], entry["successes"], entry["date"], entry["phygs_version"]) == (3, 2, "2026-11-08", "0.12.0")
    assert entry["success_ci95"][0] < 2 / 3 < entry["success_ci95"][1]
    assert entry["episodes"]["grid_table"] == dict(runs=2, successes=1, success_rate=0.5)
    assert (entry["set"], entry["rules_version"], entry["not_scored"]) == ("dev", 3, [])
    assert entry["runs"] == "output_check/20261108-1530_dev_oracle"  # Never the machine's path.


def test_runs_from_a_dirty_checkout_or_another_phygs_are_refused(tmp_path):
    suite(tmp_path / "dirty", {"a": result("grid_table", dirty=True)})
    with pytest.raises(ValueError, match="dirty checkout"):
        leaderboard.entries(tmp_path / "dirty", RULES, date="2026-11-08")
    suite(tmp_path / "other", {"a": result("grid_table", phygs="0.11.0")})
    with pytest.raises(ValueError, match="the rules pin 0.12.0"):
        leaderboard.entries(tmp_path / "other", RULES, date="2026-11-08")


def test_runs_marked_unpinned_are_refused_with_their_reasons(tmp_path):
    """A run on a PhyGS that is not the pinned release says why (``provenance.unpinned``); ``add``
    refuses its group and says why, so a non-release PhyGS never reaches the leaderboard."""
    why = "PhyGS commit 47e3edc is not v0.12.0 at 67fddf1"
    suite(tmp_path, {"a": result("grid_table"), "b": result("grid_table", commit=LATER, unpinned=[why])})
    with pytest.raises(ValueError, match=re.escape(why)):
        leaderboard.entries(tmp_path, RULES, date="2026-11-08")


def test_with_the_pinned_commit_only_runs_at_that_commit_are_accepted(tmp_path):
    """A later PhyGS commit still says 0.12.0, and a result from before ``provenance.unpinned`` does
    not say it is unpinned; the rules' ``phygs_commit`` catches it, naming the commit and the tag."""
    rules = RULES  # It carries the pinned commit.
    suite(tmp_path / "tag", {"a": result("grid_table", unpinned=[]), "b": result("grid_table")})
    (entry,) = leaderboard.entries(tmp_path / "tag", rules, date="2026-11-08")
    assert entry["n"] == 2
    suite(tmp_path / "later", {"a": result("grid_table"), "b": result("grid_table", commit=LATER)})
    with pytest.raises(ValueError) as refused:
        leaderboard.entries(tmp_path / "later", rules, date="2026-11-08")
    assert all(text in str(refused.value) for text in ("47e3edc", "v0.12.0", "67fddf1")), refused.value
    suite(tmp_path / "nocommit", {"a": result("grid_table", commit=None)})  # PhyGS outside a git checkout.
    with pytest.raises(ValueError, match="unknown"):
        leaderboard.entries(tmp_path / "nocommit", rules, date="2026-11-08")


def test_runs_that_could_not_be_scored_are_kept_and_shown(tmp_path):
    error = dict(status="error", track="privileged", agent="oracle", reason="the simulator broke")
    suite(tmp_path, {"a": result("grid_table"), "b": error, "c": None})
    (entry,) = leaderboard.entries(tmp_path, RULES, date="2026-11-08")
    assert entry["n"] == 1 and [(r["run"], r["status"]) for r in entry["not_scored"]] == [
        ("b", "error"),
        ("c", "error"),
    ]
    assert "| 1 (+2 not scored) | 1/1 |" in leaderboard.table({"entries": [entry]})


def test_a_model_agent_s_unscored_runs_are_kept_and_an_unplaceable_one_is_an_error(tmp_path):
    def vlm(model: str) -> dict:
        return result("grid_table", agent="vlm", agent_setup={"model": model, "prompt_sha256": "p1"})

    broke = dict(status="error", track="privileged", agent="vlm", reason="the simulator broke")  # No agent_setup.
    suite(tmp_path / "one", {"a": vlm("m1"), "b": broke})
    (entry,) = leaderboard.entries(tmp_path / "one", RULES, date="2026-11-08")
    assert (entry["model"], entry["n"], [r["run"] for r in entry["not_scored"]]) == ("m1", 1, ["b"])
    suite(tmp_path / "two", {"a": vlm("m1"), "b": vlm("m2"), "c": broke})
    with pytest.raises(ValueError, match="cannot tell which agent's entry run c"):
        leaderboard.entries(tmp_path / "two", RULES, date="2026-11-08")


def test_adding_a_group_again_replaces_its_entry(tmp_path):
    suite(tmp_path / "one", {"a": result("grid_table", "failure")})
    suite(tmp_path / "two", {"a": result("grid_table")})
    board = leaderboard.add({"entries": []}, leaderboard.entries(tmp_path / "one", RULES, date="2026-11-07"))
    board = leaderboard.add(board, leaderboard.entries(tmp_path / "two", RULES, date="2026-11-08"))
    assert [(e["successes"], e["date"]) for e in board["entries"]] == [(1, "2026-11-08")]


def test_the_readme_table_is_written_between_its_markers_and_checked(tmp_path):
    folder = tmp_path / "20261108-1530_dev_null"
    suite(folder, {"a": result("grid_table", "failure", agent="null")})
    rules = tmp_path / "benchmark.yaml"
    rules.write_text(json.dumps(RULES))  # JSON is YAML.
    results = tmp_path / "results.json"
    readme = tmp_path / "README.md"
    readme.write_text(f"# Title\n\n{leaderboard.BEGIN}\nold\n{leaderboard.END}\n\nAfter.\n")
    assert leaderboard.main(["add", str(folder), "--results", str(results), "--benchmark", str(rules)]) == 0
    assert leaderboard.main(["readme", "--check", "--results", str(results), "--readme", str(readme)]) == 1
    assert leaderboard.main(["readme", "--results", str(results), "--readme", str(readme)]) == 0
    assert leaderboard.main(["readme", "--check", "--results", str(results), "--readme", str(readme)]) == 0
    text = readme.read_text()
    assert "| null | `privileged` | dev | 1 | 0/1 | 0.00–0.79 |" in text and "old" not in text
    assert text.endswith(f"{leaderboard.END}\n\nAfter.\n")


def test_the_repository_readme_shows_the_results_file():
    assert leaderboard.main(["readme", "--check"]) == 0
