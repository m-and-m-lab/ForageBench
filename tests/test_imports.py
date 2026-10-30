# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The import guards. Benchmark code imports the framework's public modules only; agents import the
session only; nothing here imports Isaac Sim at module level except the two entry points."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "foragebench"
AGENTS = PACKAGE / "agents"
ENTRY_POINTS = {"run.py", "suite.py"}
# What benchmark code may take from PhyGS: the public framework modules.
PHYGS_PUBLIC = (
    "phygs.session",  # What agents get.
    "phygs.world",  # What a benchmark drives (PhyGS docs/world.md).
    "phygs.scene.registry",  # Scenes by id.
    "phygs.robots.description",
    "phygs_robot_tests.routines",
    "phygs",  # The bare package, for its version only.
)
AGENT_ALLOWED = (
    "phygs.session",
    "phygs_robot_tests.routines",
    "phygs_robot_tests",
    "numpy",
    "yaml",
    "foragebench.agents.model",
    "torch",  # The model orchestrators' optional dependencies, imported lazily.
    "transformers",
    "PIL",
    "requests",  # The OpenAI-compatible client.
)


def imported(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert not node.level, f"{path.name}: relative import"
            names.add(node.module)
    return names


def ok(name: str, heads: tuple[str, ...]) -> bool:
    if name == "phygs":  # The bare package may be imported for its version only; its modules are the list's.
        return "phygs" in heads
    return name.split(".")[0] in sys.stdlib_module_names or any(name == h or name.startswith(h + ".") for h in heads)


@pytest.mark.parametrize("path", sorted(PACKAGE.rglob("*.py")), ids=lambda p: str(p.relative_to(PACKAGE)))
def test_benchmark_code_imports_only_phygs_public_modules(path):
    for name in imported(path):
        if name.startswith("phygs"):
            assert ok(name, PHYGS_PUBLIC), f"{path.relative_to(ROOT)} imports {name}"
        if name.startswith("isaaclab") or name.startswith("omni"):
            assert path.name in ENTRY_POINTS, f"{path.relative_to(ROOT)} imports Isaac Sim ({name})"


@pytest.mark.parametrize("path", sorted(AGENTS.rglob("*.py")), ids=lambda p: str(p.relative_to(AGENTS)))
def test_agents_import_only_the_session_and_the_routines(path):
    for name in imported(path):
        assert ok(name, AGENT_ALLOWED), f"{path.name} imports {name}"
