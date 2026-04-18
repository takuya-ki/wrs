# wrs (slim fork)

A trimmed-down fork of [wanweiwei07/wrs](https://github.com/wanweiwei07/wrs),
maintained only to provide the modules required by
[wros](https://github.com/UOsaka-Harada-Laboratory/wros) (ROS 1, archived)
and [wros2](https://github.com/UOsaka-Harada-Laboratory/wros2) (ROS 2 Jazzy).

## Retained modules

- `basis/`
- `grasping/`
- `modeling/`
- `robot_sim/` (only `end_effectors/gripper/{robotiqhe,robotiq85,robotiq140}`
  and `_kinematics`)
- `visualization/panda/`

All other upstream packages, examples, and assets have been removed.
For the full system, see the upstream repository.

## Install

Used as a git submodule from the wros / wros2 repositories. See those
repositories for setup instructions.

## License

MIT — see [LICENSE](LICENSE).
