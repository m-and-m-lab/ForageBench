# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The PhyGS pin: ``third_party/phygs`` is the tagged release ``configs/benchmark_v1.yaml`` names.

Needs git, PyYAML and pytest only, so CI runs it without Isaac Sim (``.github/workflows/pin.yml``).
The commit checked is the one the index records, so the test fails before a ForageBench commit that
would pin the wrong PhyGS, not after.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]  # The ForageBench checkout.
SUBMODULE = "third_party/phygs"


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check, timeout=60)


def pinned_version() -> str:
    return str(yaml.safe_load((ROOT / "configs" / "benchmark_v1.yaml").read_text())["phygs_version"])


def recorded_commit() -> str:
    """The submodule commit in ForageBench's index (what the next commit pins)."""
    fields = git("ls-files", "-s", SUBMODULE).stdout.split()
    if not fields or fields[0] != "160000":
        pytest.fail(f"{SUBMODULE} is not a submodule in the index.")
    return fields[1]


def tag_commit(tag: str) -> str:
    """The commit a PhyGS tag names: from the submodule's own tags, else from the remote."""
    checkout = ROOT / SUBMODULE
    if (checkout / ".git").exists():
        local = git("rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}", cwd=checkout, check=False)
        if local.returncode == 0:
            return local.stdout.strip()
    url = git("config", "-f", ".gitmodules", f"submodule.{SUBMODULE}.url").stdout.strip()
    remote = git("ls-remote", "--tags", url, tag, f"{tag}^{{}}", check=False)
    if remote.returncode != 0:
        pytest.skip(f"Cannot reach {url} to resolve {tag}: {remote.stderr.strip()}")
    refs = {ref: sha for sha, ref in (line.split("\t") for line in remote.stdout.splitlines())}
    commit = refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")  # Annotated, else lightweight.
    if commit is None:
        pytest.fail(f"PhyGS has no tag {tag}: tag the release before pinning it.")
    return commit


def test_the_submodule_is_the_tagged_release_the_rules_pin():
    version = pinned_version()
    commit, tagged = recorded_commit(), tag_commit(f"v{version}")
    assert commit == tagged, (
        f"configs/benchmark_v1.yaml pins PhyGS {version} (v{version} = {tagged[:7]}) but {SUBMODULE} records"
        f" {commit[:7]}: check out v{version} in {SUBMODULE} and stage it."
    )


def test_the_pinned_commit_says_the_pinned_version():
    """The tag and the version inside the commit agree (a moved tag once pointed at a stale version)."""
    checkout = ROOT / SUBMODULE
    if not (checkout / ".git").exists():
        pytest.skip(f"{SUBMODULE} is not checked out (git submodule update --init).")
    text = git("show", f"{recorded_commit()}:phygs/__init__.py", cwd=checkout).stdout
    found = re.search(r'^__version__ = "([^"]+)"', text, re.MULTILINE)
    assert found and found.group(1) == pinned_version(), f"{SUBMODULE} says PhyGS {found and found.group(1)}."
