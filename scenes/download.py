"""Download released ForageBench scenes.

Usage:
    python -m scenes.download --all
    python -m scenes.download --scene scene_000 --scene scene_001
"""

import argparse
from pathlib import Path

from scenes.registry import SCENES_DIR

# TODO: set once scenes are published.
RELEASE_URL: str | None = None


def available_scenes() -> list[str]:
    """Scene IDs in the released benchmark."""
    # TODO: read from the release manifest.
    raise NotImplementedError("Scene release manifest is not published yet.")


def download_scene(scene_id: str, dest: Path) -> Path:
    """Download and unpack `scene_id` into `dest / scene_id`, returning that directory."""
    raise NotImplementedError("Scene release location is not published yet.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--scene", action="append", default=[], help="Scene ID (repeatable)")
    parser.add_argument("--all", action="store_true", help="Download every released scene")
    parser.add_argument("--dest", type=Path, default=SCENES_DIR)
    args = parser.parse_args()

    if not args.all and not args.scene:
        parser.error("pass --all or at least one --scene")

    scene_ids = available_scenes() if args.all else args.scene
    for scene_id in scene_ids:
        path = download_scene(scene_id, args.dest)
        print(f"{scene_id} -> {path}")


if __name__ == "__main__":
    main()
