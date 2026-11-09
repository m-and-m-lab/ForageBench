# Submitting results

The leaderboard in the [README](../README.md#-leaderboard) is written from one file,
[`leaderboard/results.json`](../leaderboard/results.json).

## What to send

Send the suite's `summary.json` and the per-run `result.json` files, from pinned runs (`unpinned` 0):
PhyGS at the pinned release, its version and commit (`configs/benchmark_v1.yaml`), with no uncommitted
changes in the PhyGS or the ForageBench checkout ([the PhyGS pin](install.md#the-phygs-pin)). We rerun
a sample of episodes with your agent before listing a result. Open a pull request or an issue on this
repository.

## How a result enters the file

From the Isaac Lab root, run the suite, then score its folder into the results file and write the
README's table from it:

```bash
FORAGEBENCH=scripts/ForageBench
OUT=$FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_dev_oracle
isaaclab -p -m foragebench suite --set dev --track privileged --agent oracle --repeats 5 --output $OUT
isaaclab -p -m foragebench leaderboard add $OUT
isaaclab -p -m foragebench leaderboard readme
```

An entry is one agent (and model and prompt) on one track and episode set: n, the successes with their
Wilson 95% interval, the per-episode results, the reached and clean rates, the runs that could not be
scored, the PhyGS and rules versions, the date of the runs and their folder. Adding the same group
again replaces its entry. `add` refuses unpinned runs, naming why (another PhyGS version or commit, a
dirty checkout), and unscored runs it cannot place in one entry. A unit test fails when the README's
table is not the file's (`isaaclab -p -m foragebench leaderboard readme --check`). The metrics are
defined in [eval/](../foragebench/eval/README.md#metrics).
