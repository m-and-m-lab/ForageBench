# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Reference agents: ``run(session)`` functions. They import only ``phygs.session``."""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable
from pathlib import Path


def load_agent(reference: str) -> tuple[str, Callable, Callable | None]:
    """(name, run function, prepare function or None) for a module of this package (``oracle``) or
    ``path/to/file.py:function``."""
    if ":" in reference:
        path, function = reference.rsplit(":", 1)
        path = Path(path).resolve(strict=True)
        module_spec = importlib.util.spec_from_file_location(f"agent_{path.stem}", path)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        name = f"{path.name}:{function}"
    else:
        module = importlib.import_module(f"foragebench.agents.{reference}")
        function, name = "run", reference
    run = getattr(module, function, None)
    if not callable(run):
        raise ValueError(f"Agent {reference!r} has no function {function!r}.")
    return name, run, getattr(module, "prepare", None)
