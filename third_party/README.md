# third_party/

External dependencies tracked as git submodules:

| Path | Repository | Used for |
|---|---|---|
| `ao-grasp/` | [m-and-m-lab/ao-grasp](https://github.com/m-and-m-lab/ao-grasp) | Grasps on articulated handles (AO-Grasp) and on objects (Contact-GraspNet) |
| `curobo/` | [m-and-m-lab/curobo](https://github.com/m-and-m-lab/curobo) | Arm motion planning |

To register them (maintainers, one-time):

```bash
git submodule add https://github.com/m-and-m-lab/ao-grasp third_party/ao-grasp
git submodule add https://github.com/m-and-m-lab/curobo third_party/curobo
```

See [`docs/install/02_foragebench.md`](../docs/install/02_foragebench.md) for install steps.
