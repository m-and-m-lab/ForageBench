# eval/

Run episodes and summarize results.

| Command | Module | Does |
| --- | --- | --- |
| `foragebench describe --episode dev/grid_table --track privileged --agent oracle` | `describe.py` | What the run would do, without the simulator; exit 1 if it would be refused (PhyGS version, missing scene). |
| `foragebench run --episode dev/grid_table --track privileged --agent oracle --output DIR` | `run.py` | One episode in one simulator process; writes `DIR/result.json` beside PhyGS's `report.json` and its recording `episode.rrd`. |
| `foragebench suite --set dev --track privileged --agent oracle --repeats 5 --output DIR` | `suite.py` | Every episode of a set, `repeats` seeds each, one process per episode (`--fresh`: one per run); `DIR/summary.json` and a table. |
| `foragebench results DIR` | `results.py` | The numbers below from the `result.json` files under a folder; writes `DIR/summary.json`. |
| `foragebench leaderboard add DIR` · `foragebench leaderboard readme` | `leaderboard.py` | Scores a suite's folder into `leaderboard/results.json` (refuses dirty runs, another PhyGS than the pin, and unscored runs it cannot place in one entry); writes the README's leaderboard table from it (`--check`: exit 1 if stale). [docs/submitting.md](../../docs/submitting.md). |

All run from the Isaac Lab root with `isaaclab -p -m foragebench <command>`.

## result.json

`status`: `completed` (scored), `setup_error` (PhyGS's start check failed before the agent started:
fix the episode or the scene) or `error` (the simulator or the World broke: rerun; such a result has
only the run's identity, its `run_id` when the run got that far, and the `reason`). `run_id` names the
run's recording (`episode.rrd`) and joins the run's files. Then `outcome` (`success`, `failure`, `not_evaluated`),
`reason`, `checks`, `reached`, `progress` (reached, opened, touched, lifted, held) and `furthest`,
`conduct`, `clean`, `ended_by`, `rules` (the thresholds' version and hash), `path_length_m` (the
evaluator's, from ground truth sampled during the run), `manipulations`, `skill_calls`,
`skill_successes`, `sim_seconds`, `wall_seconds`, `usage` (calls per client, privileged reads),
`agent_setup` (a model agent's `agent/model.json`: model, server, settings, `prompt_sha256` and
`menu_sha256`), `model` (a model agent's totals, read from the recording's `/agent/log/model/*`:
turns, pointing queries, errors by origin, tokens, seconds, retries), `scene` (id, version, USD hash), and `provenance` (PhyGS version and commit, ForageBench commit,
dirty flags, hashes of the rules, track, episode file, thresholds, robot USD and policy).

## Metrics

| Metric | Definition |
| --- | --- |
| success rate | runs with `outcome == success` over completed runs; Wilson 95% interval (the paper's IOSS) |
| reached rate | runs whose base ended within reach of the target or holds it (the paper's TS) |
| progress | the share of runs that got to each stage: reached, opened (over runs whose target started in a drawer), touched, lifted, held |
| clean rate | successes with no conduct finding, over completed runs |
| SPL | Batra et al. 2020: mean of `S_i · l_i / max(p_i, l_i)` over episodes with a stated optimal path `l_i`; `null` otherwise |
| SPL-M | SPL with each manipulation charged `spl_m_cost_per_manipulation_m` (1 m) on both sides |
| skill execution success | skill calls that ended `succeeded`, pooled over runs |
| unpinned | runs from a dirty PhyGS or ForageBench checkout; do not publish them |

Only `completed` runs are in the rates. `setup_error` and `error` runs, and run folders without a
`result.json`, are listed under `not_scored` with their reasons; a benchmark result reports them.
Runs scored under different rules versions are never pooled: `summarize` refuses the folder. Runs of
different models or prompts are never pooled either: a group is (track, agent, model, prompt hash). Rules:
`configs/benchmark_v1.yaml`.
