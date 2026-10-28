# Run from the ForageBench checkout inside the Isaac Lab container.
ISAACLAB ?= /workspace/isaaclab/isaaclab.sh
OUT ?= output_check/$(shell date +%Y%m%d-%H%M)

install:  ## PhyGS (the submodule) and ForageBench, editable, into Isaac Lab's Python.
	git submodule update --init third_party/phygs
	$(ISAACLAB) -p -m pip install -e third_party/phygs --no-deps
	$(ISAACLAB) -p -m pip install -e . --no-deps

test:  ## Unit tests (no simulator).
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(ISAACLAB) -p -m pytest tests -q -p no:cacheprovider

smoke:  ## One episode with the null agent: the simulator, the scene, the evaluator and the result file.
	$(ISAACLAB) -p foragebench/run.py --episode dev/grid_table --track privileged --agent null --output $(OUT)_smoke --headless

oracle:  ## The dev set with the oracle on the privileged track.
	$(ISAACLAB) -p foragebench/suite.py --set dev --track privileged --agent oracle --output $(OUT)_dev_oracle

.PHONY: install test smoke oracle
