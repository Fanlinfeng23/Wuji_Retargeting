# Troubleshooting

## 先确认整条链路

启动 `./scripts/start_official_manus_wuji.sh` 后，另开终端：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh

ros2 topic echo /manus_glove_0 --once --no-daemon
ros2 topic echo /hand_input --once --no-daemon
ros2 topic echo /wuji_hand/right/joint_command --once --no-daemon
ros2 topic echo /hand_0/joint_states --once --no-daemon
ros2 topic info /hand_0/joint_commands --no-daemon
```

期望：

- `/manus_glove_0` 有 MANUS 实时帧。
- `/hand_input` 有 63 个 float。
- `/wuji_hand/right/joint_command` 有 20 个 retarget 后关节角。
- `/hand_0/joint_commands` 有 `wujihand_driver_node` subscriber。
- `/hand_0/joint_states` 有 20 个实际关节位置。

## `libManusSDK_Integrated.so` 不是 ELF

报错通常类似：

```text
MANUS SDK library is missing or still a Git LFS pointer
```

处理：

```bash
sudo apt install -y git-lfs
cd ~/ros2_ws/wuji_retargeting
git lfs install
git lfs pull
./scripts/prepare_manus_sdk.sh
```

如果本机已有 MANUS SDK：

```bash
LOCAL_MANUS_SDK_DIR=/path/to/ManusSDK ./scripts/prepare_manus_sdk.sh
```

## MANUS 日志出现 `No compatible license found`

这表示 MANUS Core Integrated 启动了，但 dongle/license 没有提供 SDK 数据组件，或 dongle 被其他进程占用。

检查：

- 插入的是带 SDK 授权的 MANUS dongle。
- 关闭 MANUS Dashboard、MANUS Core、其他 `manus_data_publisher`。
- 手套已开机并与该 dongle 配对。
- 重新插拔 dongle 后只启动一个 publisher。

单独测试 MANUS：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh
ros2 run manus_ros2 manus_data_publisher
```

正常日志应包含：

```text
... is connected as MetaglovePro Dongle
license data: ...
... is connected as MetaglovePro Glove
Glove ID: ..., publishes in the last 10 seconds: ...
```

## Dongle 出现但手套不出现

处理顺序：

1. 关闭所有 MANUS 相关进程：`./scripts/stop_official_manus_wuji.sh`
2. 重新插拔 dongle。
3. 重启手套。
4. 确认手套和 dongle 已按 MANUS 官方步骤配对/校准。
5. 单独运行 `ros2 run manus_ros2 manus_data_publisher`，直到看到 glove 和 publish count。

## Wuji driver 无法连接

检查 USB：

```bash
./scripts/check_devices.sh
```

检查 SDK 只读访问：

```bash
./scripts/check_wuji_sdk.sh
```

若 `check_wuji_sdk.sh` 正常但 ROS driver 不正常，重新构建 driver：

```bash
./scripts/build_wuji_ros2_driver.sh
```

如果机器连接了多只 Wuji 手，指定序列号：

```bash
RIGHT_SERIAL=YOUR_SERIAL ./scripts/start_official_manus_wuji.sh
```

## ROS 有 joint command 但手不动

按顺序检查：

```bash
source scripts/source_env.sh
ros2 topic hz /hand_input --window 20 --no-daemon
ros2 topic hz /wuji_hand/right/joint_command --window 20 --no-daemon
ros2 topic info /hand_0/joint_commands --no-daemon
ros2 topic hz /hand_0/joint_states --window 20 --no-daemon
ros2 service call /hand_0/set_enabled wujihand_msgs/srv/SetEnabled \
  "{finger_id: 255, joint_id: 255, enabled: true}"
```

判断：

- `/hand_input` 没有数据：MANUS publisher 或 `manus_input` 问题。
- `/wuji_hand/right/joint_command` 没有数据：retarget controller 未收到合法 21 点输入。
- `/hand_0/joint_commands` 没有 subscriber：Wuji driver 没启动或 namespace 不一致。
- `/hand_0/joint_states` 没有数据：Wuji driver 没连上硬件。

## 停止残留进程

```bash
./scripts/stop_official_manus_wuji.sh
pgrep -af "manus_data_publisher|manus_input|wujihand_controller|wujihand_driver_node|ros2 launch"
```

如果仍有旧进程，手动 `kill <pid>`。

## 烟雾测试

非动作测试：

```bash
./scripts/check_environment.sh
./scripts/check_official_chain.sh
```

小幅动作测试：

```bash
./scripts/check_wuji_motion.sh --finger 1 --joint 0 --delta 0.08 --hold 0.8
```
