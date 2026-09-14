"""ForageBench metrics: TS, IOSS, skill execution success, SPL, and SPL-M."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

TRAVERSAL_TOLERANCE_M = 0.6


@dataclass(frozen=True)
class EpisodeOutcome:
    episode_id: str
    termination: str
    traversal_success: bool
    ioss: bool
    path_length: float
    """Metres travelled, including auxiliary motions to inspect or articulate scene elements."""
    optimal_path_length: float
    num_manipulation_actions: int
    optimal_manipulation_actions: int
    num_skill_calls: int
    num_skill_successes: int


def traversal_success(
    robot_xy: Sequence[float],
    target_xy: Sequence[float],
    required_interactions_ok: bool,
    signaled: bool,
    tolerance: float = TRAVERSAL_TOLERANCE_M,
) -> bool:
    """The agent reached the target location and signaled `report_found` or fail from there.

    Distance is measured in the ground plane. TODO: confirm planar vs 3D distance.
    """
    return signaled and required_interactions_ok and math.dist(robot_xy, target_xy) <= tolerance


def interactive_object_search_success(traversal: bool, reported_after_pick: bool) -> bool:
    """Traversal succeeded and `report_found` followed a successful pick of the target."""
    return traversal and reported_after_pick


def skill_execution_success(outcomes: Sequence[EpisodeOutcome]) -> float:
    """Fraction of skill calls across all episodes that returned without error."""
    calls = sum(o.num_skill_calls for o in outcomes)
    return sum(o.num_skill_successes for o in outcomes) / calls if calls else math.nan


def spl(successes: Sequence[bool], optimal: Sequence[float], actual: Sequence[float]) -> float:
    """Success weighted by path length (Batra et al., 2020): mean of S_i * l_i / max(p_i, l_i)."""
    if not (len(successes) == len(optimal) == len(actual)):
        raise ValueError("successes, optimal, and actual must have the same length")
    if not successes:
        return math.nan
    terms = [
        s * (l / max(p, l) if max(p, l) > 0 else 1.0) for s, l, p in zip(successes, optimal, actual)
    ]
    return sum(terms) / len(terms)


def manipulation_weighted_cost(
    path_length: float, num_actions: int, cost_per_action: float
) -> float:
    """Trajectory cost for SPL-M. TODO: confirm the exact cost from the paper supplement."""
    return path_length + cost_per_action * num_actions


def spl_m(outcomes: Sequence[EpisodeOutcome], cost_per_action: float) -> float:
    """SPL with manipulation actions included in both the optimal and actual trajectory cost."""
    return spl(
        [o.ioss for o in outcomes],
        [
            manipulation_weighted_cost(
                o.optimal_path_length, o.optimal_manipulation_actions, cost_per_action
            )
            for o in outcomes
        ],
        [
            manipulation_weighted_cost(o.path_length, o.num_manipulation_actions, cost_per_action)
            for o in outcomes
        ],
    )


def summarize(
    outcomes: Sequence[EpisodeOutcome], spl_m_cost_per_action: float | None = None
) -> dict[str, float]:
    """All benchmark metrics as fractions in [0, 1]. SPL-M is NaN when no action cost is given."""
    n = len(outcomes)
    return {
        "TS": sum(o.traversal_success for o in outcomes) / n if n else math.nan,
        "IOSS": sum(o.ioss for o in outcomes) / n if n else math.nan,
        "skill_execution_success": skill_execution_success(outcomes),
        "SPL": spl(
            [o.ioss for o in outcomes],
            [o.optimal_path_length for o in outcomes],
            [o.path_length for o in outcomes],
        ),
        "SPL-M": spl_m(outcomes, spl_m_cost_per_action)
        if spl_m_cost_per_action is not None
        else math.nan,
    }
