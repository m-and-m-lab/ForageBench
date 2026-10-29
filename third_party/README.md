# third_party/

| Path | Repository | Pinned to |
| --- | --- | --- |
| `phygs/` | [m-and-m-lab/PhyGS](https://github.com/m-and-m-lab/PhyGS) | the tag named in `configs/benchmark_v1.yaml` (`phygs_version`) |

Register it once PhyGS `develop` is committed and tagged (maintainers):

```bash
git submodule add -b develop https://github.com/m-and-m-lab/PhyGS.git third_party/phygs
git -C third_party/phygs checkout v0.4.0
git add .gitmodules third_party/phygs
```

Never edit inside `third_party/phygs`; bump the pin in its own commit ("Bump PhyGS to vX.Y.Z") together with `phygs_version`.
