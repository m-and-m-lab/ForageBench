# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Episodes and tracks.

An episode file is a PhyGS episode spec without ``actions`` and ``grants``, plus a ``benchmark``
block the framework never reads (the difficulty tier, the optimal path length and manipulations
for SPL). A track (``tracks/<name>.yaml``) supplies ``actions`` and ``grants``: what the agent may
do and what it is told. The manifest (``manifest_v0.yaml``) lists the episodes of each set with
their scene release. Schema and tiers: ``README.md`` beside this file.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TRACKS = HERE.parent / "tracks"
TRACK_KEYS = {"actions", "grants"}
BENCHMARK_KEYS = {"tier", "optimal_path_length_m", "optimal_manipulations"}


class Tier(IntEnum):
    """Difficulty, from the May beta's progression; the episode generator's parameters produce it."""

    VISIBLE_SAME_ROOM = 0  # Below the paper's tiers: the target is in view from the start (dev only).
    SEPARATE_ROOM_VISIBLE = 1  # Visible in another room; doors to open, no receptacles.
    SAME_ROOM_NOT_PERCEIVABLE = 2  # Hidden in a receptacle in the starting room.
    SEPARATE_ROOM_NOT_PERCEIVABLE = 3  # Hidden in a receptacle in another room.
    SEPARATE_ROOM_OCCLUDED = 4  # As 3, and occluding objects must be moved.


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
    tier: Tier | None = None
    optimal_path_length_m: float | None = None  # The SPL denominator; None until the generator states it.
    optimal_manipulations: int | None = None  # Manipulations on the optimal solution (SPL-M).


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
    scene, entry = None, {}
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
    benchmark = data.pop("benchmark", None) or {}
    if not isinstance(benchmark, dict) or set(benchmark) - BENCHMARK_KEYS:
        raise ValueError(f"{path}: the benchmark block holds {sorted(BENCHMARK_KEYS)}.")
    track_name, track_data, track_sha = load_track(track)
    spec = dict(data, **track_data)
    return Episode(
        episode_id,
        set_name,
        path,
        track_name,
        track_sha,
        spec,
        scene,
        tier=None if benchmark.get("tier") is None else Tier(int(benchmark["tier"])),
        optimal_path_length_m=benchmark.get("optimal_path_length_m"),
        optimal_manipulations=benchmark.get("optimal_manipulations"),
    )
