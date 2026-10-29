# ForageBench docs

| Need | Read |
| --- | --- |
| Install, run, write an agent | [README.md](../README.md) · [install.md](install.md) |
| What the benchmark claims and does not claim | [task_card.md](task_card.md) |
| What changed | [CHANGELOG.md](../CHANGELOG.md) |
| What is next, known gaps | [PLANS.md](../PLANS.md) |
| Rules for contributors and coding agents (submodule discipline) | [AGENTS.md](../AGENTS.md) |
| Writing a model agent: the orchestrator loop, the skills, the prompts | [foragebench/agents/model/](../foragebench/agents/model/__init__.py) · [README](../README.md#%EF%B8%8F-writing-an-agent) |
| The framework: session, skills, robots, scenes, robot tests | [PhyGS docs](https://github.com/m-and-m-lab/PhyGS/blob/develop/docs/README.md) (`third_party/phygs/docs/`) |

## Design record (`design/`, offline HTML; open with `python3 -m http.server --directory docs/design/<page>`)

| Page | What it records |
| --- | --- |
| [repo_split/](design/repo_split/index.html) | How the lab's development tree became PhyGS and ForageBench: mapping, submodule rules, READMEs, steps, decisions (2026-10-28). |
| [benchmark_audit/](design/benchmark_audit/index.html) | The audit of the benchmark design: scope, difficulty, knowability, transfer, the changes it asked for. |
| [benchmark_positioning/](design/benchmark_positioning/index.html) | Where ForageBench stands among 40+ 2024–2026 benchmarks and frameworks; the audited review; prioritized improvements. |

The framework/benchmark split and the evaluator design pages live with the framework (PhyGS `docs/design/`).

## Research notes (`research/`)

`research/reports/`: what agentic robotics frameworks need, what frontier models demand of them, frontier planners with VLA executors. `research/notes/`: the benchmark design survey (interactive-search task designs, policy-evaluation frameworks, LLM-agent benchmarks, adoption and governance) and the audit's notes. Sources are cited inside; treat secondary sources as such.
