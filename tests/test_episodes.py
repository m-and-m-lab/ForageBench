# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Episodes, tracks and the manifest load into PhyGS specs; the benchmark rules pin a PhyGS version and
commit, and a run is pinned only on that release."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from phygs.world import EpisodeSpec, summary

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
    for target in (episode.answer["target"], *episode.answer.get("matches", ())):
        assert all(target not in str(value) for value in public.values()), f"{key}: the public task names {target!r}"


TAG = "67fddf15b94f7b99e82be2257b89d83fefdcb4ac"  # PhyGS v0.12.0's commit.
LATER = "47e3edc" + "0" * 33  # A later PhyGS commit whose __version__ still says 0.12.0.
PIN = {"phygs_version": "0.12.0", "phygs_commit": TAG}


def test_the_rules_pin_a_phygs_version_and_its_commit():
    """A run is pinned when PhyGS's version and commit are the rules' (a later commit keeps the
    version string). A run on another PhyGS is marked unpinned, never refused: the refusal is gone."""
    version, commit = RULES["phygs_version"], RULES.get("phygs_commit")
    assert isinstance(version, str), f"phygs_version {version!r}: quote it, a YAML number is not a version"
    assert isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), f"phygs_commit {commit!r}"
    assert foragebench.pin_problems(RULES, version, {"commit": commit, "dirty": False}) == []
    assert not hasattr(foragebench, "check_phygs_version")


def test_a_run_is_pinned_only_at_the_pinned_version_and_commit_of_a_clean_checkout():
    """One plain reason per problem, in order: the version, the commit (unknown outside a git checkout,
    never a crash), uncommitted changes. ``code`` is PhyGS's ``code_version``: commit and dirty."""
    assert foragebench.pin_problems(PIN, "0.12.0", {"commit": TAG, "dirty": False}) == []
    assert foragebench.pin_problems(PIN, "0.12.0", {"commit": TAG, "dirty": None}) == []  # Not known dirty.
    (later,) = foragebench.pin_problems(PIN, "0.12.0", {"commit": LATER, "dirty": False})
    assert all(text in later for text in ("47e3edc", "v0.12.0", "67fddf1")), later
    version, commit = foragebench.pin_problems(PIN, "0.13.0.dev0", {"commit": LATER, "dirty": False})
    assert "0.13.0.dev0" in version and "0.12.0" in version, version
    assert all(text in commit for text in ("47e3edc", "v0.12.0", "67fddf1")), commit
    (unknown,) = foragebench.pin_problems(PIN, "0.12.0", {"commit": None, "dirty": None})
    assert "unknown" in unknown, unknown
    (dirty,) = foragebench.pin_problems(PIN, "0.12.0", {"commit": TAG, "dirty": True})
    assert "uncommitted" in dirty, dirty
    first, second, third = foragebench.pin_problems(PIN, "0.13.0.dev0", {"commit": LATER, "dirty": True})
    assert "0.13.0.dev0" in first and "47e3edc" in second and "uncommitted" in third, (first, second, third)


def test_the_pin_line_names_both_pins_and_says_pinned_or_why_not():
    """``foragebench version`` and ``describe`` print it: the pinned and the installed version, each at its
    short commit, then ``pinned`` or ``unpinned (<the reasons>)``."""
    pinned = foragebench.pin_text(PIN, "0.12.0", {"commit": TAG, "dirty": False})
    assert pinned.startswith("pinned 0.12.0 at 67fddf1") and "installed 0.12.0 at 67fddf1" in pinned, pinned
    assert pinned.endswith(": pinned"), pinned
    code = {"commit": LATER, "dirty": False}
    later = foragebench.pin_text(PIN, "0.13.0.dev0", code)
    assert later.startswith("pinned 0.12.0 at 67fddf1") and "installed 0.13.0.dev0 at 47e3edc" in later, later
    assert ": unpinned (" in later and not later.endswith(": pinned"), later
    assert all(reason in later for reason in foragebench.pin_problems(PIN, "0.13.0.dev0", code)), later
    unknown = foragebench.pin_text(PIN, "0.12.0", {"commit": None, "dirty": None})  # No git checkout: no crash.
    assert ": unpinned (" in unknown and "unknown" in unknown, unknown
