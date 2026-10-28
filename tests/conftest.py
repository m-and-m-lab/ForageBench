from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # The ForageBench checkout; PhyGS is installed or at third_party/phygs.
for path in (ROOT, ROOT / "third_party" / "phygs"):
    if str(path) not in sys.path and path.is_dir():
        sys.path.insert(0, str(path))
