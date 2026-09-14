"""Episode termination conditions."""

from collections.abc import Sequence
from enum import StrEnum

from agent.interface.skills import SkillCall, SkillName, SkillResult, SkillStatus


class TerminationReason(StrEnum):
    REPORTED_FOUND = "reported_found"
    COLLISION = "collision"
    OUT_OF_BOUNDS = "out_of_bounds"
    INCOMPATIBLE_SKILL = "incompatible_skill"
    REPEATED_SKILL = "repeated_skill"
    WRONG_REPORT = "wrong_report"
    STEP_BUDGET = "step_budget"


def repeated_skill(history: Sequence[SkillCall], limit: int = 3) -> bool:
    """True once the last `limit` calls are identical.

    Calls count as repeats only if both skill and arguments match, so navigating to three different
    rooms in a row does not terminate. TODO: confirm this matches the benchmark definition.
    """
    return len(history) >= limit and all(call == history[-1] for call in history[-limit:])


def check_skill_termination(
    result: SkillResult,
    history: Sequence[SkillCall],
    target_prim_path: str,
    max_repeated_skill: int = 3,
) -> TerminationReason | None:
    """Termination conditions that depend only on the skill calls. `history` includes `result.call`."""
    if result.status is SkillStatus.INCOMPATIBLE:
        return TerminationReason.INCOMPATIBLE_SKILL
    if result.call.name is SkillName.REPORT_FOUND:
        if result.call.args.get("object") == target_prim_path:
            return TerminationReason.REPORTED_FOUND
        return TerminationReason.WRONG_REPORT
    if repeated_skill(history, max_repeated_skill):
        return TerminationReason.REPEATED_SKILL
    return None
