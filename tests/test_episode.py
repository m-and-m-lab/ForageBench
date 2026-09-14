from pathlib import Path

from tasks.episode import DifficultyTier, load_episode

EXAMPLE = Path(__file__).parents[1] / "tasks" / "examples" / "episode.yaml"


def test_load_example_episode():
    episode = load_episode(EXAMPLE)
    assert episode.tier is DifficultyTier.SEPARATE_ROOM_VISIBLE
    assert episode.target.description == "a ceramic mug"
    assert episode.target.position == (4.2, -1.5, 0.9)
    assert [i.skill for i in episode.required_interactions] == ["open_door"]
