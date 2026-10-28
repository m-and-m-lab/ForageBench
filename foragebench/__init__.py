# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""ForageBench: a benchmark for interactive object search on the PhyGS simulation framework.

The benchmark imports ``phygs`` (the framework) and ``phygs_robot_tests.routines`` (for the oracle);
PhyGS never imports the benchmark. A benchmark version pins a PhyGS version
(``configs/benchmark_v1.yaml``); :func:`check_phygs_version` refuses to run against another.
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


def check_phygs_version(expected: str) -> None:
    """Refuse to run against a PhyGS other than the benchmark's pinned version."""
    found = phygs_version()
    if found != str(expected):
        raise RuntimeError(
            f"ForageBench pins PhyGS {expected} (configs/benchmark_v1.yaml) but phygs {found} is installed;"
            " install third_party/phygs at the pinned tag (make install)."
        )
