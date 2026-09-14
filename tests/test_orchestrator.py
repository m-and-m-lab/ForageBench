import pytest

from agent.interface.skills import SkillName
from agent.orchestrators.base import build_system_prompt, parse_skill_call


def test_parse_skill_call_strips_code_fence():
    call = parse_skill_call(
        '```json\n{"skill": "open_drawer", "args": {"reference": "drawer_1"}}\n```'
    )
    assert call.name is SkillName.OPEN_DRAWER
    assert call.args == {"reference": "drawer_1"}


@pytest.mark.parametrize(
    "text",
    [
        "no json here",
        '{"skill": "fly", "args": {}}',
        '{"skill": "navigate", "args": {"reference": "kitchen"}}',
    ],
)
def test_parse_skill_call_rejects_invalid(text):
    with pytest.raises(ValueError):
        parse_skill_call(text)


def test_system_prompt_reflects_condition():
    unknown = build_system_prompt("a ceramic mug", None, affordance_prior=False)
    known = build_system_prompt("a ceramic mug", (1.0, 2.0, 0.5), affordance_prior=False)
    assert "location is unknown" in unknown
    assert "[1.0, 2.0, 0.5]" in known
    assert "navigate(target)" in known
