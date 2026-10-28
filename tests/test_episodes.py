# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Episodes, tracks and the manifest load into PhyGS specs; the benchmark rules pin a PhyGS version."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from phygs.episodes.spec import EpisodeSpec

import foragebench
from foragebench.episodes import TRACKS, load_episode, load_track, manifest_entries
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
    assert task.goal == "retrieve" and task.target
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


def test_the_rules_pin_the_installed_phygs_version():
    foragebench.check_phygs_version(RULES["phygs_version"])
    with pytest.raises(RuntimeError, match="pins PhyGS 9.9.9"):
        foragebench.check_phygs_version("9.9.9")
