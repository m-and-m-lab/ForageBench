# 1. IsaacLab Docker container

ForageBench targets **IsaacLab 2.3 / IsaacSim 5.1**. Follow the official
[IsaacLab Docker guide](https://isaac-sim.github.io/IsaacLab/main/source/deployment/docker.html)
to build and start the base container:

```bash
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
git checkout v2.3.0  # TODO: confirm the exact tag used for the benchmark
python docker/container.py start
python docker/container.py enter base
```

## Mounting ForageBench

TODO: document how the ForageBench checkout and `scenes/data/` are mounted into the container
(e.g. a bind mount added to IsaacLab's `docker/docker-compose.yaml`).

## Hardware

TODO: list minimum GPU / VRAM requirements. Scenes use ray-traced lighting, and full-house scenes
are expensive to render.
