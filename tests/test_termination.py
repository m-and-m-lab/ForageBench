from agent.interface.skills import SkillCall, SkillName, SkillResult, SkillStatus
from eval.termination import TerminationReason, check_skill_termination, repeated_skill

TARGET = "/World/scene_000/objects/ceramic_mug"


def nav(target: str) -> SkillCall:
    return SkillCall(SkillName.NAVIGATE, {"target": target})


def test_repeated_skill_requires_identical_consecutive_calls():
    assert repeated_skill([nav("kitchen")] * 3)
    assert not repeated_skill([nav("kitchen")] * 2)
    assert not repeated_skill([nav("kitchen"), nav("bedroom"), nav("kitchen")])


def test_report_found_checks_target():
    right = SkillCall(SkillName.REPORT_FOUND, {"object": TARGET})
    wrong = SkillCall(SkillName.REPORT_FOUND, {"object": "/World/scene_000/objects/bottle"})
    assert (
        check_skill_termination(SkillResult(right, SkillStatus.SUCCESS), [right], TARGET)
        is TerminationReason.REPORTED_FOUND
    )
    assert (
        check_skill_termination(SkillResult(wrong, SkillStatus.SUCCESS), [wrong], TARGET)
        is TerminationReason.WRONG_REPORT
    )


def test_incompatible_skill_terminates():
    call = SkillCall(SkillName.OPEN_DRAWER, {"reference": "/World/scene_000/doors/kitchen_door"})
    result = SkillResult(call, SkillStatus.INCOMPATIBLE)
    assert check_skill_termination(result, [call], TARGET) is TerminationReason.INCOMPATIBLE_SKILL


def test_ordinary_failure_does_not_terminate():
    call = nav("kitchen")
    assert check_skill_termination(SkillResult(call, SkillStatus.FAILED), [call], TARGET) is None
