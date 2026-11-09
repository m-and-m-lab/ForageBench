# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""ForageBench: a benchmark for interactive object search on the PhyGS simulation framework.

The benchmark imports PhyGS's public surfaces (``phygs.world``, ``phygs.session``,
``phygs.composite``, ``phygs.scene``, ``phygs.robots``), never its robot tests. PhyGS never imports
the benchmark. A benchmark version pins a PhyGS release, its version and its tag's commit
(``configs/benchmark_v1.yaml``); :func:`pin_problems` says why an installed PhyGS is not it. A run
on another PhyGS goes ahead, marked unpinned: its results are not publishable.
"""

from __future__ import annotations

__version__ = "1.0.0.dev0"


def phygs_version() -> str:
    """The installed PhyGS version (``phygs.__version__``)."""
    import phygs

    version = getattr(phygs, "__version__", None)
    if version is None:
        raise RuntimeError("The installed phygs has no __version__; ForageBench needs PhyGS 0.3.0 or later.")
    return version


def phygs_code() -> dict:
    """The imported PhyGS checkout's ``commit`` and whether it has uncommitted changes (``dirty``),
    None where git cannot read it: what its runs record as ``provenance.code``."""
    from pathlib import Path

    import phygs
    from phygs.world import code_version

    return code_version(Path(phygs.__file__).resolve().parents[1])


def dirty_problem(project: str) -> str:
    """The reason a checkout of ``project`` (PhyGS, ForageBench) with uncommitted changes is unpinned."""
    return f"a dirty checkout of {project}, with uncommitted changes"


def commit_problem(commit: str | None, rules: dict) -> str | None:
    """Why a PhyGS ``commit`` is not the pinned release's (``rules["phygs_commit"]``); None when it is."""
    if "phygs_commit" not in rules:
        raise ValueError("The benchmark rules name no phygs_commit (configs/benchmark_v1.yaml).")
    version, tag = str(rules["phygs_version"]), str(rules["phygs_commit"])
    if commit is None:
        return f"the PhyGS commit is unknown (git could not read the checkout): not shown to be v{version} at {tag[:7]}"
    if commit != tag:
        return f"PhyGS commit {commit[:7]} is not v{version} at {tag[:7]}"
    return None


def pin_problems(rules: dict, version: str, code: dict) -> list[str]:
    """Why a PhyGS at ``version`` with ``code`` (``commit``, ``dirty``) is not the release the rules
    pin (``phygs_version`` at ``phygs_commit``); empty when it is. Install ``third_party/phygs`` at the
    pinned tag for a pinned run (docs/install.md)."""
    problems = []
    if version != str(rules["phygs_version"]):
        problems.append(f"PhyGS {version} is installed; the rules pin {rules['phygs_version']}")
    commit = commit_problem(code.get("commit"), rules)
    if commit:
        problems.append(commit)
    if code.get("dirty"):
        problems.append(dirty_problem("PhyGS"))
    return problems


def pin_text(rules: dict, version: str, code: dict) -> str:
    """One line: the pinned and the installed PhyGS, then pinned, or unpinned and why."""
    problems = pin_problems(rules, version, code)
    state = "pinned" if not problems else f"unpinned ({'; '.join(problems)})"
    pinned = f"{rules['phygs_version']} at {str(rules['phygs_commit'])[:7]}"
    return f"pinned {pinned}, installed {version} at {(code.get('commit') or 'unknown')[:7]}: {state}"
