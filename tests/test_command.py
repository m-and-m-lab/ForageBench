# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The ``foragebench`` command: its help, its version and ``describe``, none of which starts Isaac Sim."""

from __future__ import annotations

from pathlib import Path

import yaml

from foragebench.__main__ import main

RULES = Path(__file__).resolve().parents[1] / "configs" / "benchmark_v1.yaml"


def test_help_lists_every_command_and_an_unknown_one_is_refused(capsys):
    assert main(["--help"]) == 0
    usage = capsys.readouterr().out
    assert all(f"foragebench {name}" in usage for name in ("describe", "run", "suite", "results", "scenes", "version"))
    assert main(["deploy"]) == 2 and main([]) == 2


def test_version_names_the_pinned_and_the_installed_phygs(capsys):
    assert main(["version"]) == 0
    pinned = yaml.safe_load(RULES.read_text())["phygs_version"]
    assert f"PhyGS pinned {pinned}, installed" in capsys.readouterr().out


def test_describe_resolves_a_run_without_the_simulator(capsys):
    assert main(["describe", "--episode", "dev/grid_table", "--track", "gt_localization", "--agent", "null"]) == 0
    lines = dict(line.split(None, 1) for line in capsys.readouterr().out.splitlines())
    assert lines["episode"].startswith("dev/grid_table") and lines["rules"] == "version 1"
    assert "grants ['gt_localization']" in lines["track"] and lines["agent"] == "null"


def test_describe_refuses_a_run_against_another_phygs(tmp_path, capsys):
    rules = yaml.safe_load(RULES.read_text()) | {"phygs_version": "9.9.9"}
    other = tmp_path / "benchmark.yaml"
    other.write_text(yaml.safe_dump(rules))
    args = ["describe", "--episode", "dev/grid_table", "--agent", "null", "--benchmark", str(other)]
    assert main(args) == 1 and "REFUSED" in capsys.readouterr().out
