# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Episodes and tracks.

An episode file is a PhyGS episode spec without ``actions`` and ``grants``: the scene (a release
of the scene dataset, by id and version, or a fixture), the robot's start, the objects moved
before the run, the task block, what the agent observes, the budget and the seed. A track
(``tracks/<name>.yaml``) supplies ``actions`` and ``grants``: what the agent may do and what it is
told. The manifest (``manifest_v0.yaml``) lists the episodes of each set with their scene release.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TRACKS = HERE.parent / "tracks"
TRACK_KEYS = {"actions", "grants"}


@dataclass(frozen=True)
class Episode:
    """One episode on one track, ready for ``EpisodeSpec.from_dict(spec, base=path.parent)``."""

    id: str
    set: str | None
    path: Path
    track: str
    track_sha256: str
    spec: dict
    scene: str | None = None  # The manifest's scene release (``id@version``), when listed.


def load_track(name_or_path: str) -> tuple[str, dict, str]:
    """(name, {actions, grants}, sha256) of a track by name (``tracks/<name>.yaml``) or path."""
    path = Path(name_or_path)
    if not path.suffix:
        path = TRACKS / f"{name_or_path}.yaml"
    if not path.is_file():
        names = sorted(p.stem for p in TRACKS.glob("*.yaml"))
        raise FileNotFoundError(f"No track {name_or_path!r}; the tracks are {names} or a path.")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or set(data) != TRACK_KEYS:
        raise ValueError(f"{path}: a track is {{actions, grants}}.")
    return path.stem, data, hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_entries(manifest: Path) -> dict[str, tuple[str, dict]]:
    """``set/id`` -> (set, entry) for every episode the manifest lists."""
    data = yaml.safe_load(manifest.read_text())
    if data.get("schema") != 0 or not isinstance(data.get("sets"), dict):
        raise ValueError(f"{manifest}: expected manifest schema 0 with sets.")
    entries = {}
    for set_name, items in data["sets"].items():
        for entry in items:
            if not {"id", "file"} <= set(entry):
                raise ValueError(f"{manifest}: an episode entry needs id and file ({set_name}).")
            entries[f"{set_name}/{entry['id']}"] = (set_name, entry)
    return entries


def load_episode(reference: str, *, track: str, manifest: Path) -> Episode:
    """An episode by manifest id (``dev/grid_table``) or file path, on ``track``."""
    entries = manifest_entries(manifest)
    scene = None
    if reference in entries:
        set_name, entry = entries[reference]
        path, scene = manifest.parent / entry["file"], entry.get("scene")
        episode_id = entry["id"]
    else:
        path = Path(reference)
        if not path.is_file():
            raise FileNotFoundError(f"No episode {reference!r}: not in {manifest} ({sorted(entries)}) and not a file.")
        set_name, episode_id = None, path.stem
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: an episode is a mapping.")
    if TRACK_KEYS & set(data):
        raise ValueError(f"{path}: actions and grants come from the track, not the episode file.")
    track_name, track_data, track_sha = load_track(track)
    spec = dict(data, **track_data)
    return Episode(episode_id, set_name, path, track_name, track_sha, spec, scene)
