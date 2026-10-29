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
    assert summary["runs"] == 3 and summary["errors"] == ["d"]
    assert (
        group["spl_runs"] == 2 and group["spl"] == pytest.approx(0.5) and group["success_rate"] == pytest.approx(2 / 3)
    )
