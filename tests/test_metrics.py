# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""SPL, SPL-M and skill execution success (carried over from the May beta's eval/metrics.py)."""

from __future__ import annotations

import pytest

from foragebench.eval.results import skill_execution_success, spl, spl_m, summarize


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
