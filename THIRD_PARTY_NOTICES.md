# Third-Party Notices

This repository vendors official Wuji/MANUS-related source so the MANUS-to-Wuji
teleoperation path can be built reproducibly.

## Wuji Hand Teleop

Path: `wuji-hand-teleop`

Upstream: https://github.com/wuji-technology/wuji-hand-teleop

Vendored commit: `3fa58481e971bf1588b57751ea44d99abe1d95b5`

License file: `wuji-hand-teleop/LICENSE`

Notes:

- The nested upstream `.git` directory is intentionally removed so this
  repository can be uploaded as a normal GitHub repository.
- MANUS SDK `.so` files are Git LFS assets in the upstream project. Run
  `./scripts/prepare_manus_sdk.sh` after cloning.

## Wuji Retargeting

Path: `third_party/wuji_official/wuji_retargeting`

License file: `third_party/wuji_official/LICENSE.wuji-retargeting.txt`

The runtime API used by this project is `wuji_retargeting.Retargeter`.

## Wuji Hand Teleop Retarget Configs

Path: `third_party/wuji_official/config`

License file: `third_party/wuji_official/LICENSE.wuji-hand-teleop.txt`

The primary runtime configs are also available in:

```text
wuji-hand-teleop/src/output_devices/wujihand_output/config/
```

## Wuji ROS2 Driver

Path: `third_party/wujihandros2`

The driver source is copied from Wuji's official `wujihandros2` repository.
Check `third_party/wujihandros2/README.md` and the upstream project for
driver-specific license and release details.

## MANUS SDK

Path:

```text
wuji-hand-teleop/src/input_devices/manus_input/manus_ros2/ManusSDK
```

The MANUS SDK headers and shared libraries are redistributed through the
official Wuji teleop source layout. Users must comply with MANUS SDK licensing
terms and use a MANUS license dongle that includes SDK access.
