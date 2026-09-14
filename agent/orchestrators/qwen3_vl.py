"""Qwen3-VL-8B-Instruct orchestrator, run locally with Hugging Face transformers."""

from agent.interface.skills import SkillCall
from agent.orchestrators.base import Observation, Orchestrator, OrchestratorConfig, parse_skill_call


class Qwen3VLOrchestrator(Orchestrator):
    def __init__(self, config: OrchestratorConfig):
        super().__init__(config)
        # TODO: load the model and processor from config.model
        # (transformers Qwen3VLForConditionalGeneration + AutoProcessor).
        self.model = None
        self.processor = None

    def act(self, observation: Observation) -> SkillCall:
        # TODO: build a chat from self.system_prompt, observation.images, and observation.history,
        # generate up to config.max_new_tokens, and parse the reply.
        response = self._generate(observation)
        return parse_skill_call(response)

    def _generate(self, observation: Observation) -> str:
        raise NotImplementedError
