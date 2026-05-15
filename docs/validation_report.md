# Validation Report

Date: 2026-05-15

Repository path:

```text
/home/user/ros2_ws/wuji_retargeting
```

## Passed

Static checks:

```bash
bash -n scripts/*.sh
/usr/bin/python3 -m py_compile launch/manus_wuji_right.launch.py
```

Environment:

```bash
./scripts/check_environment.sh
```

Result:

```text
[check] python modules ok
[check] ros2: /opt/ros/humble/bin/ros2
[check] environment looks usable
```

Wuji ROS2 driver build:

```bash
./scripts/build_wuji_ros2_driver.sh
```

Result:

```text
Summary: 4 packages finished
```

Official teleop overlay build:

```bash
./scripts/build_official_teleop.sh
```

Result:

```text
Summary: 7 packages finished
```

Overlay source:

```text
official_teleop_ws/src/controller         -> wuji-hand-teleop/src/controller
official_teleop_ws/src/manus_ros2_msgs    -> wuji-hand-teleop/src/input_devices/manus_input/manus_ros2_msgs
official_teleop_ws/src/manus_ros2         -> wuji-hand-teleop/src/input_devices/manus_input/manus_ros2
official_teleop_ws/src/manus_input_py     -> wuji-hand-teleop/src/input_devices/manus_input/manus_input_py
official_teleop_ws/src/wujihand_output    -> wuji-hand-teleop/src/output_devices/wujihand_output
official_teleop_ws/src/tianji_output      -> wuji-hand-teleop/src/output_devices/tianji_output
official_teleop_ws/src/wuji_teleop_bringup -> wuji-hand-teleop/src/wuji_teleop_bringup
```

Official chain smoke test:

```bash
./scripts/check_official_chain.sh
```

Result:

```text
[check] official package visibility
[check] official launch arguments
[check] official retargeter import
[check] retargeter ok
[check] official chain is buildable and discoverable
```

Release self-contained check:

```bash
./scripts/prepare_manus_sdk.sh
```

Result:

```text
[ok] copied MANUS SDK from /home/user/ros2_ws/src/ROS2/ManusSDK
```

The vendored MANUS SDK libraries are real ELF shared objects, not Git LFS
pointer files.

Launch argument validation:

```bash
ros2 launch /home/user/ros2_ws/wuji_retargeting/launch/manus_wuji_right.launch.py --show-args
```

Important defaults:

```text
right_serial: ''
right_hand_name: hand_0
```

This wrapper launches the official nodes for one right hand and uses
`wujihandros2` auto-detect for the hand serial.

## Hardware Visibility

Earlier hardware validation showed both required USB devices:

```text
0483:2000 STMicroelectronics WUJIHAND
3325:0049 Manus VR Sensor Dongle
```

During the final release-tree test after cleanup, `check_devices.sh` did not
see Wuji USB and did not initially see the MANUS dongle:

```text
[warn] MANUS dongle not found with vendor id 3325
[warn] Wuji hand not found as 0483:2000
```

The short launch test later recognized the MANUS dongle and license, but Wuji
hardware was not connected:

```text
0xA36F84C5 is connected as MetaglovePro Dongle
license data: ...
No device found with specified vendor id (0x0483)
```

## Official Full-Chain Launch

Command:

```bash
./scripts/start_official_manus_wuji.sh
```

Observed successful Wuji side:

```text
Using firmware version: 1.2.1, SN: LQSQJR.260417.005
Connected to WujiHand (right)
WujiHand driver started (state: 1000.0 Hz, diagnostics: 10.0 Hz)
Right hand connected (via wujihandros2)
```

Observed official nodes:

```text
wujihand_driver_node
manus_data_publisher
manus_input
wujihand_controller
```

Observed successful MANUS side:

```text
0xA36F84C5 is connected as MetaglovePro Dongle
0x8FDEA3A3 is connected as MetaglovePro Glove
Glove ID: 2413732771, publishes in the last 10 seconds: 959
```

Observed ROS topics:

```text
/manus_glove_0 [manus_ros2_msgs/msg/ManusGlove]
/hand_input [std_msgs/msg/Float32MultiArray]
/wuji_hand/right/joint_command [sensor_msgs/msg/JointState]
/hand_0/joint_commands [sensor_msgs/msg/JointState]
/hand_0/joint_states [sensor_msgs/msg/JointState]
```

Verified:

- `/manus_glove_0` publishes live 25-node right-hand frames from MANUS.
- `/hand_input` publishes 63 floats in MediaPipe right-hand order.
- `/wuji_hand/right/joint_command` publishes 20 retargeted joint angles from
  official `wujihand_controller`.
- `/hand_0/joint_commands` has one publisher and one `wujihand_driver_node`
  subscriber.
- `/hand_0/joint_states` publishes 20 Wuji joint positions.

## Local Input Compatibility

The local MANUS ROS message uses semantic node ids `0..24` with
`chain_type`/`joint_type`. Wuji's official example mapping expects fixed ids
such as `(1, 22, 23, 24, 25, 3, 4, ...)`. A small fallback was added to
`wuji-hand-teleop/src/input_devices/manus_input/manus_input_py/manus_input_py/manus_input_node.py`
so this local message format is converted into the same official MediaPipe
`/hand_input` contract. The Wuji retargeter and controller remain the official
method.

## Current Runtime State

At the end of the latest repository cleanup, the official chain was stopped:

```text
pgrep -af "manus_data_publisher|manus_input|wujihand_controller|wujihand_driver_node|ros2 launch"
# no output
```

Generated build/log directories are ignored by `.gitignore` and should be
removed before commit if a clean release tree is desired. Re-run:

```bash
./scripts/prepare_manus_sdk.sh
./scripts/build_wuji_ros2_driver.sh
./scripts/build_official_teleop.sh
./scripts/start_official_manus_wuji.sh
```
