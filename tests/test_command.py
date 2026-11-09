# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The ``foragebench`` command: its help, its version and ``describe``, none of which starts Isaac Sim."""

from __future__ import annotations

from pathlib import Path

import yaml

import foragebench
from foragebench.__main__ import main
from foragebench.tasks.retrieve import rules_version

RULES = Path(__file__).resolve().parents[1] / "configs" / "benchmark_v1.yaml"


def test_help_lists_every_command_and_an_unknown_one_is_refused(capsys):
    assert main(["--help"]) == 0
    usage = capsys.readouterr().out
    assert all(f"foragebench {name}" in usage for name in ("describe", "run", "suite", "results", "scenes", "version"))
    assert main(["deploy"]) == 2 and main([]) == 2


def test_version_names_the_pinned_and_the_installed_phygs_and_whether_they_match(capsys):
    """``PhyGS`` and :func:`foragebench.pin_text` for the live install: the pinned version at its commit, the
    installed version, then pinned or unpinned with the reasons. Either verdict passes here."""
    assert main(["version"]) == 0
    rules = yaml.safe_load(RULES.read_text())
    out = capsys.readouterr().out
    assert f"PhyGS pinned {rules['phygs_version']} at {rules['phygs_commit'][:7]}" in out, out
    assert f"installed {foragebench.phygs_version()}" in out and (": pinned" in out or ": unpinned (" in out), out


def test_describe_resolves_a_run_without_the_simulator(capsys):
    assert main(["describe", "--episode", "dev/grid_table", "--track", "gt_localization", "--agent", "null"]) == 0
    lines = dict(line.split(None, 1) for line in capsys.readouterr().out.splitlines())
    assert lines["episode"].startswith("dev/grid_table") and lines["rules"] == f"version {rules_version()}"
    assert "grants ['gt_localization']" in lines["track"] and lines["agent"] == "null"


def test_describe_marks_a_run_against_another_phygs_unpinned_and_does_not_refuse_it(tmp_path, capsys):
    """A PhyGS other than the pin may run, marked unpinned and kept off the leaderboard; the exit code
    is the scene's alone (the scene is present here)."""
    rules = yaml.safe_load(RULES.read_text()) | {"phygs_version": "9.9.9"}
    other = tmp_path / "benchmark.yaml"
    other.write_text(yaml.safe_dump(rules))
    args = ["describe", "--episode", "dev/grid_table", "--agent", "null", "--benchmark", str(other)]
    code, out = main(args), capsys.readouterr().out
    assert code == 0 and "REFUSED" not in out, out
    row = dict(line.split(None, 1) for line in out.splitlines())["PhyGS"]
    assert row.startswith(f"pinned 9.9.9 at {rules['phygs_commit'][:7]}") and ": unpinned (" in row, row
