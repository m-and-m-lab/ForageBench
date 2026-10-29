# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The scenes the benchmark uses: which releases the manifest needs, whether each is present, and
fetching the missing ones through PhyGS (``phygs.scene.fetch``). PhyGS owns the registry and the
dataset; this module only asks for what the episodes name.

    ./isaaclab.sh -p -m foragebench scenes list
    ./isaaclab.sh -p -m foragebench scenes fetch
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from phygs.scene.registry import scene_file

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SceneNeed:
    id: str
    version: str | None  # None: a fixture or an unversioned folder.
    episodes: tuple[str, ...]
    path: Path | None  # Where the registry finds it now, or None when missing.
    missing: str  # Why it is missing, or "".


def needs(manifest: Path) -> list[SceneNeed]:
    """The scene releases the manifest's episodes name, with their presence in the scene roots."""
    data = yaml.safe_load(manifest.read_text())
    by_scene: dict[tuple[str, str | None], list[str]] = {}
    for set_name, items in data["sets"].items():
        for entry in items:
            episode = yaml.safe_load((manifest.parent / entry["file"]).read_text())
            scene = episode["scene"]
            key = (str(scene["id"]), None if scene.get("version") is None else str(scene["version"]))
            by_scene.setdefault(key, []).append(f"{set_name}/{entry['id']}")
    out = []
    for (scene_id, version), episodes in sorted(by_scene.items()):
        try:
            path, missing = scene_file(scene_id, version), ""
        except (FileNotFoundError, ValueError) as error:
            path, missing = None, str(error)
        out.append(SceneNeed(scene_id, version, tuple(episodes), path, missing))
    return out


def fetch(need: SceneNeed) -> int:
    """Fetch one release through PhyGS's fetcher (a versioned release only)."""
    if need.version is None:
        raise ValueError(f"{need.id} is a fixture or local folder; nothing to fetch")
    command = [
        sys.executable,
        "-m",
        "phygs.scene.fetch",
        "fetch",
        "--scene_id",
        need.id,
        "--scene_version",
        need.version,
    ]
    return subprocess.run(command).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("list", "fetch"))
    parser.add_argument("--manifest", type=Path, default=ROOT / "foragebench" / "episodes" / "manifest_v0.yaml")
    args = parser.parse_args(argv)
    code = 0
    for need in needs(args.manifest):
        label = need.id if need.version is None else f"{need.id}@{need.version}"
        if need.path is not None:
            print(f"{label:<28} present  {need.path}  ({', '.join(need.episodes)})")
        elif args.command == "fetch" and need.version is not None:
            print(f"{label:<28} fetching ...", flush=True)
            code = fetch(need) or code
        else:
            print(f"{label:<28} MISSING  {need.missing}  ({', '.join(need.episodes)})")
            code = 1 if args.command == "list" else code
    return code


if __name__ == "__main__":
    sys.exit(main())
