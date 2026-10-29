# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Episodes, tracks and the manifest load into PhyGS specs; the benchmark rules pin a PhyGS version."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from phygs.world.spec import EpisodeSpec
from phygs.world.task import summary

import foragebench
from foragebench.episodes import PUBLIC_TASK_KEYS, TRACKS, load_episode, load_track, manifest_entries
from foragebench.tasks import load_task

ROOT = Path(__file__).resolve().parents[1]
RULES = yaml.safe_load((ROOT / "configs" / "benchmark_v1.yaml").read_text())
MANIFEST = ROOT / RULES["manifest"]


@pytest.mark.parametrize("key", sorted(manifest_entries(MANIFEST)))
@pytest.mark.parametrize("track", sorted(p.stem for p in TRACKS.glob("*.yaml")))
def test_every_manifest_episode_loads_on_every_track(key, track):
    episode = load_episode(key, track=track, manifest=MANIFEST)
    spec = EpisodeSpec.from_dict(episode.spec, base=episode.path.parent)
    assert spec.actions and spec.grants is not None
    task = load_task(spec.task)
    assert task.goal == "retrieve" and task.target == episode.answer["target"]
    assert episode.optimal_manipulations >= 1  # The file's optimal block.
    assert "answer" not in episode.spec and "optimal" not in episode.spec  # Stripped before PhyGS sees the spec.
    if episode.scene and "@" in episode.scene:  # A scene release: the spec pins the same version.
        scene_id, version = episode.scene.split("@")
        assert (spec.scene.id, spec.scene.version) == (scene_id, version)


def test_tracks_supply_actions_and_grants_and_episode_files_never_do(tmp_path):
    name, data, digest = load_track("privileged")
    assert name == "privileged" and set(data) == {"actions", "grants"} and len(digest) == 64
    with pytest.raises(FileNotFoundError, match="tracks are"):
        load_track("telepathy")
    bad = tmp_path / "ep.yaml"
    bad.write_text("schema: 3\nid: x\ngrants: [known_map]\n")
    with pytest.raises(ValueError, match="come from the track"):
        load_episode(str(bad), track="privileged", manifest=MANIFEST)
    public = "task: {goal: retrieve, description: the box}\n"
    for text, message in (
        (
            "task: {goal: retrieve, description: the box, target: box}\nanswer: {target: box}\n",
            "the target is in answer",
        ),
        (public, "answer block"),
        (public + "answer: {target: box, hidden_in: top}\n", "answer block"),
        (public + "answer: {target: box}\noptimal: {tier: 2}\n", "optimal block"),
    ):
        bad.write_text("schema: 3\nid: x\n" + text)
        with pytest.raises(ValueError, match=message):
            load_episode(str(bad), track="privileged", manifest=MANIFEST)


@pytest.mark.parametrize("key", sorted(manifest_entries(MANIFEST)))
def test_nothing_hidden_reaches_the_agent(key):
    """The agent's session gets the task's goal and description (PhyGS's ``summary``), and nothing in
    them names the target: its scene name is the episode's hidden answer."""
    episode = load_episode(key, track="gt_localization", manifest=MANIFEST)
    task = load_task(EpisodeSpec.from_dict(episode.spec, base=episode.path.parent).task)
    public = summary(task)
    assert set(public) == PUBLIC_TASK_KEYS and public == episode.public_task
    target = episode.answer["target"]
    assert all(target not in str(value) for value in public.values()), f"{key}: the public task names {target!r}"


def test_the_rules_pin_the_installed_phygs_version():
    foragebench.check_phygs_version(RULES["phygs_version"])
    with pytest.raises(RuntimeError, match="pins PhyGS 9.9.9"):
        foragebench.check_phygs_version("9.9.9")
