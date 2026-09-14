"""Gemini Robotics ER-1.6 orchestrator, using the Google GenAI SDK.

Reads `GEMINI_API_KEY` from the environment.
"""

from agent.interface.skills import SkillCall
from agent.orchestrators.base import Observation, Orchestrator, OrchestratorConfig, parse_skill_call


class GeminiRoboticsEROrchestrator(Orchestrator):
    def __init__(self, config: OrchestratorConfig):
        super().__init__(config)
        # TODO: create a google.genai Client.
        self.client = None

    def act(self, observation: Observation) -> SkillCall:
        # TODO: send self.system_prompt, observation.images, and observation.history to
        # config.model and parse the reply.
        response = self._generate(observation)
        return parse_skill_call(response)

    def _generate(self, observation: Observation) -> str:
        raise NotImplementedError
