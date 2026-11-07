# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The import guards. Benchmark code imports the framework's public modules only, by their exact
names, and never the robot tests; the reference agents (``foragebench/agents``) import only the
session and the composite skills of PhyGS; nothing here imports Isaac Sim at module level except the
two entry points."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "foragebench"
AGENTS = PACKAGE / "agents"
ENTRY_POINTS = {"run.py", "suite.py"}
# What benchmark code may take from PhyGS: the public framework modules, exactly these names.
PHYGS_PUBLIC = {
    "phygs.session",  # What agents get.
    "phygs.composite",  # The composite skills over the session (agent-side).
    "phygs.world",  # What a benchmark drives (PhyGS docs/world.md); never its submodules.
    "phygs.scene.registry",  # Scenes by id.
    "phygs.robots.description",
    "phygs",  # The bare package, for its version only.
}
AGENT_ALLOWED = (
    "phygs.session",
    "phygs.composite",
    "numpy",
    "yaml",
    "foragebench.agents.model",
    "PIL",
    "requests",  # The OpenAI-compatible client.
    "anthropic",  # The Claude client (optional: `pip install anthropic`).
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
        assert not name.startswith("phygs_robot_tests"), f"{path.relative_to(ROOT)} imports the robot tests ({name})"
        if name.startswith("phygs"):
            assert name in PHYGS_PUBLIC, f"{path.relative_to(ROOT)} imports {name}, not a public PhyGS module"
        if name.startswith("isaaclab") or name.startswith("omni"):
            assert path.name in ENTRY_POINTS, f"{path.relative_to(ROOT)} imports Isaac Sim ({name})"


@pytest.mark.parametrize("path", sorted(AGENTS.rglob("*.py")), ids=lambda p: str(p.relative_to(AGENTS)))
def test_agents_import_only_the_session_and_the_composite_skills(path):
    for name in imported(path):
        assert ok(name, AGENT_ALLOWED), f"{path.name} imports {name}"
