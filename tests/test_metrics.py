# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""SPL, SPL-M and skill execution success (carried over from the May beta's eval/metrics.py)."""

from __future__ import annotations

import pytest

from foragebench.eval.results import model_totals, skill_execution_success, spl, spl_m, summarize, table


def test_spl_weights_success_by_path_efficiency():
    assert spl([True, True, False], [10.0, 10.0, 10.0], [10.0, 20.0, 5.0]) == pytest.approx(0.5)
    assert spl([], [], []) is None
    with pytest.raises(ValueError):
        spl([True], [1.0, 2.0], [1.0])


def run(**over) -> dict:
    base = dict(
        outcome="success",
        path_length_m=10.0,
        optimal_path_length_m=10.0,
        manipulations=2,
        optimal_manipulations=2,
        skill_calls=4,
        skill_successes=3,
        track="t",
        agent="a",
        episode="e",
        clean=True,
        sim_seconds=1.0,
        provenance={},
    )
    return base | over


def test_spl_m_charges_manipulations_on_both_sides_and_pools_skill_success():
    assert spl_m([run(), run(manipulations=4)], cost_per_manipulation_m=5.0) == pytest.approx((1.0 + 20 / 30) / 2)
    assert spl_m([run(optimal_path_length_m=None)], 1.0) is None
    assert skill_execution_success([run(), run(skill_calls=6, skill_successes=6)]) == pytest.approx(0.9)
    assert skill_execution_success([run(skill_calls=0, skill_successes=0)]) is None


def test_summary_reports_spl_only_for_rated_episodes(tmp_path):
    import json

    for name, result in (
        ("a", run()),
        ("b", run(outcome="failure", path_length_m=5.0)),
        ("c", run(optimal_path_length_m=None)),
    ):
        (tmp_path / name).mkdir()
        (tmp_path / name / "result.json").write_text(json.dumps(result))
    (tmp_path / "d").mkdir()  # A run that broke: no result.
    summary = summarize(tmp_path)
    group = summary["groups"][0]
    assert summary["runs"] == 3 and summary["not_scored"]["error"] == [dict(run="d", reason="no result.json")]
    assert (
        group["spl_runs"] == 2 and group["spl"] == pytest.approx(0.5) and group["success_rate"] == pytest.approx(2 / 3)
    )


def write_runs(folder, runs: dict) -> None:
    import json

    for name, result in runs.items():
        (folder / name).mkdir()
        (folder / name / "result.json").write_text(json.dumps(result))


def test_only_completed_runs_are_in_the_rates_and_the_others_are_listed_with_their_reasons(tmp_path):
    write_runs(
        tmp_path,
        {
            "a": run(status="completed"),
            "b": run(status="completed", outcome="failure"),
            "c": run(status="setup_error", outcome="not_evaluated", reason="2 bodies still move"),
            "d": run(status="error", outcome=None, reason="RuntimeError: the planner died"),
        },
    )
    summary = summarize(tmp_path)
    assert summary["runs"] == 2 and summary["groups"][0]["success_rate"] == pytest.approx(0.5)
    assert summary["not_scored"]["setup_error"] == [dict(run="c", reason="2 bodies still move")]
    assert summary["not_scored"]["error"] == [dict(run="d", reason="RuntimeError: the planner died")]


def test_runs_scored_under_different_rules_versions_are_never_pooled(tmp_path):
    write_runs(tmp_path, {"a": run(rules={"version": 1}), "b": run(rules={"version": 2})})
    with pytest.raises(ValueError, match="rules versions"):
        summarize(tmp_path)


def test_runs_of_different_models_or_prompts_are_never_pooled(tmp_path):
    claude = dict(model="claude-opus-5-5", prompt_sha256="p1" * 32)
    write_runs(
        tmp_path,
        {
            "a": run(agent="vlm", agent_setup=claude),
            "b": run(agent="vlm", agent_setup=claude, outcome="failure"),
            "c": run(agent="vlm", agent_setup=dict(claude, model="Qwen/Qwen3.5-9B")),
            "d": run(agent="vlm", agent_setup=dict(claude, prompt_sha256="p2" * 32)),
            "e": run(agent="oracle"),
        },
    )
    groups = summarize(tmp_path)["groups"]
    found = sorted((g["agent"], g["model"], (g["prompt_sha256"] or "")[:2], g["runs"]) for g in groups)
    assert found == [
        ("oracle", None, "", 1),
        ("vlm", "Qwen/Qwen3.5-9B", "p1", 1),
        ("vlm", "claude-opus-5-5", "p1", 2),
        ("vlm", "claude-opus-5-5", "p2", 1),
    ]
    assert "model claude-opus-5-5, prompt p1p1p1p1p1p1" in table(summarize(tmp_path))


def test_a_model_run_s_totals_come_from_the_records_it_kept():
    from types import SimpleNamespace

    def kept(topic, **record):
        return SimpleNamespace(topic=topic, record=record)

    log = [
        kept("model/setup", model="m"),
        kept(
            "model/turn", usage={"input_tokens": 100, "output_tokens": 20, "details": {"x": 1}}, seconds=2.0, retries=1
        ),
        kept("model/point", usage={"input_tokens": 50}, seconds=0.5, retries=0),
        kept("model/error", origin="model"),
        kept("model/error", origin="api"),
        kept("model/error", origin="model"),
        kept("notes"),
    ]
    totals = model_totals(log)
    assert totals == dict(
        turns=1,
        points=1,
        errors={"model": 2, "api": 1},
        tokens={"input_tokens": 150, "output_tokens": 20},
        seconds=2.5,
        retries=1,
    )
    assert model_totals([kept("notes")]) is None  # An agent that kept no model record.


def test_an_unknown_status_is_an_error(tmp_path):
    write_runs(tmp_path, {"a": run(status="finished")})
    with pytest.raises(ValueError, match="unknown status"):
        summarize(tmp_path)


def test_the_reached_rate_and_the_progress_funnel(tmp_path):
    stages = ("reached", "opened", "touched", "lifted", "held")
    full = dict.fromkeys(stages, True)
    stopped = dict(full, touched=False, lifted=False, held=False)  # Reached and opened, then gave up.
    in_the_open = dict(full, opened=None)  # A target on a table: nothing to open.
    write_runs(
        tmp_path,
        {
            "a": run(reached=True, progress=full),
            "b": run(outcome="failure", reached=True, progress=stopped),
            "c": run(reached=True, progress=in_the_open),
            "d": run(outcome="failure", reached=False, progress=dict.fromkeys(stages, False) | {"opened": None}),
        },
    )
    group = summarize(tmp_path)["groups"][0]
    assert group["reached_rate"] == pytest.approx(0.75)
    assert group["progress"]["opened"] == pytest.approx(1.0)  # Two runs with something to open, both opened it.
    assert group["progress"]["held"] == pytest.approx(0.5) and group["progress"]["touched"] == pytest.approx(0.5)


def test_an_episodes_repeats_in_one_process_are_read_from_their_seed_folders(tmp_path):
    """``run --repeats``: one folder per episode, a ``s<seed>`` folder per repeat; a repeat with no
    result is an error, and the episode folder's own files and logs are not runs."""
    episode = tmp_path / "dev_grid_table"
    episode.mkdir()
    write_runs(episode, {"s0": run(), "s1": run(outcome="failure"), "s2": run()})
    (episode / "s3" / "nav2").mkdir(parents=True)  # A repeat that never wrote its result.
    (episode / "environment.yaml").write_text("{}")
    summary = summarize(tmp_path)
    assert summary["runs"] == 3 and summary["groups"][0]["success_rate"] == pytest.approx(2 / 3)
    assert summary["not_scored"]["error"] == [dict(run="dev_grid_table/s3", reason="no result.json")]


def test_grasps_count_holds_of_a_body_not_jaw_links_or_commands():
    from foragebench.eval.results import grasps

    jaws = lambda body, first, last: [  # noqa: E731 - one entry per jaw link, as the report writes them.
        dict(body=body, link="arm_link_fngr", first_s=first, last_s=last),
        dict(body=body, link="arm_link_wr1", first_s=first + 0.02, last_s=last - 0.02),
    ]
    assert grasps([]) == 0
    assert grasps(jaws("drawer", 10.0, 14.0) + jaws("target", 30.0, 60.0)) == 2  # Open, then pick.
    assert grasps(jaws("target", 30.0, 31.0) + jaws("target", 40.0, 50.0)) == 2  # A second try on the target.


def test_the_summary_counts_finishes_the_evaluator_did_not_confirm(tmp_path):
    write_runs(
        tmp_path,
        {
            "a": run(ended_by="finish"),
            "b": run(ended_by="finish", outcome="failure"),  # The agent said done; the target was not held.
            "c": run(ended_by="budget", outcome="failure"),
        },
    )
    group = summarize(tmp_path)["groups"][0]
    assert (group["finishes"], group["false_finishes"]) == (2, 1)


def test_a_run_is_unpinned_for_the_reasons_it_recorded_a_dirty_checkout_or_another_commit():
    """A run writes why it is unpinned (``provenance.unpinned``); a result from before that key is
    unpinned for a dirty checkout, as before, and, given rules with ``phygs_commit``, for a PhyGS commit
    other than the pinned one (a later commit still says 0.12.0)."""
    from foragebench.eval.results import pin_reasons, unpinned

    tag, later = "67fddf15b94f7b99e82be2257b89d83fefdcb4ac", "47e3edc" + "0" * 33

    def ran(commit=tag, phygs_dirty=False, foragebench_dirty=False, **more) -> dict:
        code = {"commit": commit, "dirty": phygs_dirty}
        mine = {"commit": "f" * 40, "dirty": foragebench_dirty}
        return run(provenance=dict(phygs_version="0.12.0", code=code, foragebench=mine, **more))

    why = "PhyGS commit 47e3edc is not v0.12.0 at 67fddf1"
    assert pin_reasons(ran(later, unpinned=[why])) == [why] and unpinned(ran(later, unpinned=[why]))
    assert pin_reasons(ran(unpinned=[])) == [] and not unpinned(ran(unpinned=[]))  # A run on the release.
    assert pin_reasons(ran()) == [] and not unpinned(ran())  # An older result from clean checkouts.
    assert pin_reasons(ran(phygs_dirty=True)) == ["a dirty checkout of PhyGS, with uncommitted changes"]
    assert unpinned(ran(phygs_dirty=True))
    assert pin_reasons(ran(foragebench_dirty=True)) == ["a dirty checkout of ForageBench, with uncommitted changes"]
    assert unpinned(ran(foragebench_dirty=True))
    rules = {"phygs_version": "0.12.0", "phygs_commit": tag}
    assert pin_reasons(ran(), rules) == []
    with pytest.raises(ValueError, match="phygs_commit"):  # Rules without the pinned commit are an error.
        pin_reasons(ran(later), {"phygs_version": "0.12.0"})
    (commit,) = pin_reasons(ran(later), rules)
    assert all(text in commit for text in ("47e3edc", "v0.12.0", "67fddf1")), commit
    (unknown,) = pin_reasons(ran(None), rules)
    assert all(text in unknown for text in ("unknown", "v0.12.0", "67fddf1")), unknown


def test_given_the_rules_the_summary_counts_an_older_run_at_another_commit_as_unpinned(tmp_path):
    """An older result (no ``provenance.unpinned``) from clean checkouts at a later PhyGS commit: the
    summary counts it unpinned only when it is given the rules, as ``foragebench results`` does."""
    tag, later = "67fddf15b94f7b99e82be2257b89d83fefdcb4ac", "47e3edc" + "0" * 33
    clean = {"commit": "f" * 40, "dirty": False}
    older = run(
        status="completed",
        provenance=dict(phygs_version="0.12.0", code={"commit": later, "dirty": False}, foragebench=clean),
    )
    write_runs(tmp_path, {"a": older})
    rules = {"phygs_version": "0.12.0", "phygs_commit": tag}
    assert summarize(tmp_path)["groups"][0]["unpinned"] == 0
    assert summarize(tmp_path, 1.0, rules)["groups"][0]["unpinned"] == 1
