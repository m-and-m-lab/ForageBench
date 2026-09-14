"""Write benchmark results and format metric summaries."""

import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from eval.metrics import EpisodeOutcome


def write_results(
    outcomes: Sequence[EpisodeOutcome], summary: dict[str, float], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"summary": summary, "episodes": [asdict(o) for o in outcomes]}, indent=2)
    )


def format_summary(summary: dict[str, float]) -> str:
    return "\n".join(f"{name:>24}: {100 * value:6.2f}%" for name, value in summary.items())
