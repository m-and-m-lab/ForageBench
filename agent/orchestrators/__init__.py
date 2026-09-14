"""VLM orchestrators evaluated as ForageBench baselines."""

from pathlib import Path

import yaml

from agent.orchestrators.base import Orchestrator, OrchestratorConfig


def load_orchestrator(config_path: Path) -> Orchestrator:
    """Build an orchestrator from a YAML config in `agent/configs/`."""
    data = yaml.safe_load(Path(config_path).read_text())
    kind = data.pop("type")
    config = OrchestratorConfig(**data)

    # Import lazily so each orchestrator's model dependencies stay optional.
    if kind == "qwen3_vl":
        from agent.orchestrators.qwen3_vl import Qwen3VLOrchestrator

        return Qwen3VLOrchestrator(config)
    if kind == "gemini_robotics_er":
        from agent.orchestrators.gemini_robotics_er import GeminiRoboticsEROrchestrator

        return GeminiRoboticsEROrchestrator(config)
    raise ValueError(f"Unknown orchestrator type {kind!r}")
