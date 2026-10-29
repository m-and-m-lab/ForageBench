# eval/

Run episodes and summarize results.

| Command | Does |
| --- | --- |
| `run.py --episode dev/grid_table --track privileged --agent oracle --output DIR` | One episode in one simulator process; writes `DIR/result.json` beside PhyGS's `report.json` and `audit.jsonl`. |
| `suite.py --set dev --track privileged --agent oracle --repeats 5 --output DIR` | Every episode of a set, `repeats` seeds each, one process per run; `DIR/summary.json` and a table. |
| `eval/results.py` | `summarize(folder)`: the numbers below from the `result.json` files under a folder. |

All run from the Isaac Lab root with `./isaaclab.sh -p $FORAGEBENCH/foragebench/eval/<script>`.

## result.json

`outcome` (`success`, `failure`, `not_evaluated`), `reason`, `checks`, `conduct`, `clean`,
`ended_by`, `tier`, `path_length_m` (integrated from ground truth), `manipulations`, `skill_calls`,
`skill_successes`, `sim_seconds`, `wall_seconds`, `usage` (calls per client, privileged reads),
`scene` (id, version, USD hash), and `provenance` (PhyGS version and commit, ForageBench commit,
dirty flags, hashes of the rules, track, episode file, thresholds, robot USD and policy).

## Metrics

| Metric | Definition |
| --- | --- |
| success rate | runs with `outcome == success` over completed runs; Wilson 95% interval |
| clean rate | successes with no conduct finding, over completed runs |
| SPL | Batra et al. 2020: mean of `S_i · l_i / max(p_i, l_i)` over episodes with a stated optimal path `l_i`; `null` otherwise |
| SPL-M | SPL with each manipulation charged `spl_m_cost_per_manipulation_m` (1 m) on both sides |
| skill execution success | skill calls that ended `succeeded`, pooled over runs |
| unpinned | runs from a dirty PhyGS or ForageBench checkout; do not publish them |

Runs that broke (no `result.json`) are listed as errors and are not in the rates; a benchmark result
reports them. Rules: `configs/benchmark_v1.yaml`.
