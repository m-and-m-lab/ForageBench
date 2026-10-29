# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Qwen3-VL orchestrator, run locally with Hugging Face transformers (``pip install transformers accelerate``).

Untested against a model in this repository's CI: the chat format follows the Qwen3-VL processor's
documented ``apply_chat_template`` with image content parts. Report mismatches as issues.
"""

from __future__ import annotations

from foragebench.agents.model.orchestrator import (
    Observation,
    Orchestrator,
    OrchestratorConfig,
    SkillCall,
    history_text,
    parse_skill_call,
)


class Qwen3VLOrchestrator(Orchestrator):
    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        super().__init__(config or OrchestratorConfig(model="Qwen/Qwen3-VL-8B-Instruct"))
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        self.processor = AutoProcessor.from_pretrained(self.config.model)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            self.config.model, torch_dtype=torch.bfloat16, device_map="auto"
        )

    def act(self, observation: Observation) -> SkillCall:
        return parse_skill_call(self._generate(observation))

    def _generate(self, observation: Observation) -> str:
        from PIL import Image

        images = [Image.fromarray(image) for image in observation.images.values()]
        content = [{"type": "image", "image": image} for image in images]
        content.append({"type": "text", "text": self._turn_text(observation)})
        messages = [
            {"role": "system", "content": [{"type": "text", "text": self.system_prompt}]},
            {"role": "user", "content": content},
        ]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
        ).to(self.model.device)
        output = self.model.generate(**inputs, max_new_tokens=self.config.max_new_tokens)
        return self.processor.batch_decode(output[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True)[0]

    def _turn_text(self, observation: Observation) -> str:
        cameras = ", ".join(observation.images)
        pose = "unknown" if observation.pose is None else [round(v, 3) for v in observation.pose]
        return (
            f"Cameras (in order): {cameras}. Your pose (x, y, heading): {pose}.\n"
            f"Previous skill results:\n{history_text(observation.history, self.config.history)}\n"
            "Reply with one JSON object."
        )
