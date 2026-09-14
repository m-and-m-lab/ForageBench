import math

import pytest

from eval.metrics import EpisodeOutcome, skill_execution_success, spl, summarize, traversal_success


def outcome(**overrides) -> EpisodeOutcome:
    fields = {
        "episode_id": "scene_000_tier1",
        "termination": "reported_found",
        "traversal_success": True,
        "ioss": True,
        "path_length": 10.0,
        "optimal_path_length": 10.0,
        "num_manipulation_actions": 2,
        "optimal_manipulation_actions": 2,
        "num_skill_calls": 4,
        "num_skill_successes": 3,
    }
    return EpisodeOutcome(**(fields | overrides))


def test_spl_weights_success_by_path_efficiency():
    assert spl([True, True, False], [10.0, 10.0, 10.0], [10.0, 20.0, 5.0]) == pytest.approx(0.5)


def test_spl_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        spl([True], [1.0, 2.0], [1.0])


def test_spl_empty_is_nan():
    assert math.isnan(spl([], [], []))


def test_traversal_success_uses_tolerance_and_requires_signal():
    assert traversal_success((0.0, 0.0), (0.6, 0.0), required_interactions_ok=True, signaled=True)
    assert not traversal_success(
        (0.0, 0.0), (0.61, 0.0), required_interactions_ok=True, signaled=True
    )
    assert not traversal_success(
        (0.0, 0.0), (0.0, 0.0), required_interactions_ok=False, signaled=True
    )
    assert not traversal_success(
        (0.0, 0.0), (0.0, 0.0), required_interactions_ok=True, signaled=False
    )


def test_skill_execution_success_pools_calls_across_episodes():
    outcomes = [
        outcome(num_skill_calls=4, num_skill_successes=3),
        outcome(num_skill_calls=6, num_skill_successes=6),
    ]
    assert skill_execution_success(outcomes) == pytest.approx(0.9)


def test_summarize_without_manipulation_cost_leaves_spl_m_nan():
    summary = summarize([outcome(), outcome(ioss=False, traversal_success=False)])
    assert summary["TS"] == summary["IOSS"] == summary["SPL"] == pytest.approx(0.5)
    assert math.isnan(summary["SPL-M"])
