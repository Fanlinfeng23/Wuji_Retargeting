# MANUS Metagloves Pro Teleoperation for Wuji Hand

这是一个面向发布的 ROS2 仓库，用 MANUS Metagloves Pro 实时遥操 Wuji 灵巧手。运行链路严格采用 Wuji 官方 [`wuji-hand-teleop`](https://github.com/wuji-technology/wuji-hand-teleop) 的 MANUS 手套遥操方法，本仓库只做单右手启动封装、环境脚本、设备检查和 MANUS 消息兼容。

```text
MANUS Metagloves Pro
  -> manus_ros2/manus_data_publisher
  -> /manus_glove_0
  -> manus_input_py/manus_input
  -> /hand_input                         # MediaPipe 21 x 3, right hand first
  -> controller/wujihand_controller
  -> wujihand_output.WujiHandController
  -> wuji_retargeting.Retargeter
  -> /hand_0/joint_commands
  -> wujihandros2/wujihand_driver_node
  -> Wuji Hand
```

## 当前实现是否等同官方方法

Retargeting 核心等同官方方法：

- 使用官方 `Retargeter.from_yaml(retarget_manus_right.yaml, "right")`。
- 输入为 MediaPipe 顺序 `(21, 3)` 手部关键点。
- 优化器为官方 `AdaptiveOptimizerAnalytical`。
- 输出为 20 个 Wuji 关节角，通过 `sensor_msgs/msg/JointState.position` 发给 `/hand_0/joint_commands`。
- `controller/wujihand_node.py`、`wujihand_output`、`wujihandros2` 驱动均使用官方源码。

本仓库仅有两处非算法封装：

- `launch/manus_wuji_right.launch.py`：把官方双手 launch 收敛为单右手 `/hand_0`，减少新用户配置成本。
- `manus_input_node.py` 中的兼容 fallback：当 MANUS ROS2 消息使用 `chain_type/joint_type` 语义节点编号时，仍转换成官方 `/hand_input` 的 21 点 MediaPipe 合约。Retargeter、优化器、Wuji 控制器没有改。

详细方法分析见 [docs/retargeting_method.md](docs/retargeting_method.md)。

## 仓库内容

```text
config/                         # 单右手配置
launch/                         # 单右手官方链路 wrapper
scripts/                        # 安装、构建、检查、启动脚本
src/                            # Wuji 只读/小幅动作检查工具
third_party/wuji_official/       # Wuji 官方 retargeting Python 包
third_party/wujihandros2/        # Wuji 官方 ROS2 driver
wuji-hand-teleop/                # vendored Wuji 官方 teleop 源码
legacy/                         # 早期实验代码，仅历史参考
```

官方 teleop 源码来源：`wuji-technology/wuji-hand-teleop` commit `3fa58481e971bf1588b57751ea44d99abe1d95b5`。

## 硬件准备

1. 给 Wuji 灵巧手供电，并连接 USB 到电脑。
2. 插入 MANUS SDK 授权 dongle。
3. 打开 MANUS Metagloves Pro 手套，确认手套已与 dongle 配对。
4. 如果之前打开过 MANUS Dashboard、MANUS Core 或其他 `manus_data_publisher`，先关闭，避免 dongle 被占用。

按 MANUS 官方 Metagloves Pro 文档，首次使用需要完成设备上电、dongle 连接、配对和校准；按 Wuji 官方文档，Wuji 手需要 USB 可见、供电正常、SDK/ROS2 driver 能访问设备。

## 软件环境

推荐环境：

- Ubuntu 22.04
- ROS2 Humble
- Python 3.10
- `wujihandcpp` 1.6.0 或兼容版本
- MANUS SDK license dongle，且 license 包含 SDK 功能

安装系统依赖：

```bash
sudo apt update
sudo apt install -y \
  git git-lfs curl usbutils build-essential cmake \
  python3-pip python3-colcon-common-extensions libncurses-dev \
  ros-humble-desktop ros-humble-ament-cmake ros-humble-rclpy \
  ros-humble-std-msgs ros-humble-sensor-msgs ros-humble-geometry-msgs \
  ros-humble-rosidl-default-generators ros-humble-tf2-ros
```

安装 Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

安装 Wuji C++ SDK。若你的系统尚未安装 `wujihandcpp`，从 Wuji 官方 release 下载并安装对应版本，例如：

```bash
curl -L -o /tmp/wujihandcpp.deb \
  https://github.com/wuji-technology/wujihandpy/releases/download/v1.6.0/wujihandcpp-1.6.0-amd64.deb
sudo apt install -y /tmp/wujihandcpp.deb
```

## 下载与准备仓库

```bash
mkdir -p ~/ros2_ws
cd ~/ros2_ws
git clone <YOUR_REPO_URL> wuji_retargeting
cd ~/ros2_ws/wuji_retargeting
```

MANUS SDK `.so` 是大文件。官方 `wuji-hand-teleop` 使用 Git LFS 管理这些库，因此 clone 后必须准备真实二进制：

```bash
git lfs install
git lfs pull
./scripts/prepare_manus_sdk.sh
```

如果本机已有 MANUS ROS2 SDK，也可以指定本地 SDK：

```bash
LOCAL_MANUS_SDK_DIR=/path/to/ManusSDK ./scripts/prepare_manus_sdk.sh
```

安装 udev 规则，使 MANUS dongle 和 Wuji USB 设备无需 sudo 即可访问：

```bash
./scripts/setup_udev_rules.sh
```

执行后重新插拔 MANUS dongle 和 Wuji USB 线。

## 构建

```bash
cd ~/ros2_ws/wuji_retargeting

./scripts/build_wuji_ros2_driver.sh
./scripts/build_official_teleop.sh
./scripts/check_environment.sh
./scripts/check_official_chain.sh
```

`build_official_teleop.sh` 会在本仓库 `official_teleop_ws` 中构建这些官方包：`manus_ros2_msgs`、`manus_ros2`、`manus_input_py`、`controller`、`wujihand_output`、`tianji_output`、`wuji_teleop_bringup`。远端用户不需要预先构建 `/home/user/ros2_ws/install`。

## 设备检查

检查 USB：

```bash
./scripts/check_devices.sh
```

期望看到：

- MANUS dongle：vendor id `3325`，常见 `3325:0049`
- Wuji hand：常见 `0483:2000`

检查 Wuji SDK 只读访问：

```bash
./scripts/check_wuji_sdk.sh
```

可选小幅动作测试：

```bash
./scripts/check_wuji_motion.sh --finger 1 --joint 0 --delta 0.08 --hold 0.8
```

这个命令会短暂使能一个关节、小幅移动、再回到初始位置。确认手周围无障碍后再运行。

## 一键启动遥操

```bash
cd ~/ros2_ws/wuji_retargeting
export ROS_DOMAIN_ID=30
./scripts/start_official_manus_wuji.sh
```

成功时日志应包含：

```text
... is connected as MetaglovePro Dongle
... is connected as MetaglovePro Glove
Glove ID: ..., publishes in the last 10 seconds: ...
Connected to WujiHand (right)
Right hand connected (via wujihandros2)
```

如果需要指定 Wuji 手序列号：

```bash
RIGHT_SERIAL=LQSQJR.260417.005 ./scripts/start_official_manus_wuji.sh
```

不设置 `RIGHT_SERIAL` 时使用 Wuji ROS2 driver 的自动发现。

停止：

```bash
./scripts/stop_official_manus_wuji.sh
```

## 运行时验收

另开一个终端：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh

ros2 topic list -t --no-daemon
ros2 topic echo /manus_glove_0 --once --no-daemon
ros2 topic echo /hand_input --once --no-daemon
ros2 topic echo /wuji_hand/right/joint_command --once --no-daemon
ros2 topic echo /hand_0/joint_states --once --no-daemon
ros2 topic info /hand_0/joint_commands --no-daemon
```

期望结果：

- `/manus_glove_0` 有 MANUS 实时帧。
- `/hand_input` 是 63 个 float，即单右手 `21 x xyz`。
- `/wuji_hand/right/joint_command` 是 20 个 retarget 后关节角。
- `/hand_0/joint_commands` 有 `wujihand_driver_node` 订阅。
- `/hand_0/joint_states` 有 20 个 Wuji 实际关节位置。

## 分终端调试

终端 1，启动 Wuji driver：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh
ros2 run wujihand_driver wujihand_driver_node \
  --ros-args -r __ns:=/hand_0 -p serial_number:=""
```

终端 2，启动 MANUS publisher：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh
ros2 run manus_ros2 manus_data_publisher
```

终端 3，启动 MANUS 到 MediaPipe 转换：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh
./scripts/start_official_manus_input.sh
```

终端 4，启动官方 Wuji retarget controller：

```bash
cd ~/ros2_ws/wuji_retargeting
source scripts/source_env.sh
./scripts/start_official_wujihand_controller.sh
```

## 常见问题

详细排查见 [docs/troubleshooting.md](docs/troubleshooting.md)。

最常见问题：

- `No compatible license found`：MANUS dongle 没有暴露 SDK license，或 dongle 被其他 MANUS Core/Publisher 占用。
- `libManusSDK_Integrated.so` 不是 ELF：没有执行 `git lfs pull` 或没有真实 MANUS SDK 库。
- ROS topic 有命令但手不动：检查 `/hand_0/joint_commands` 是否有 subscriber、`/hand_0/joint_states` 是否更新、Wuji hand 是否供电并成功 `Connected to WujiHand`。

## 官方资料

- Wuji hand teleop: https://github.com/wuji-technology/wuji-hand-teleop
- Wuji 手官方文档: https://docs.wuji.tech/docs/zh/wuji-hand/latest/
- MANUS Metagloves Pro: https://docs.manus-meta.com/3.1.0/Products/Metagloves%20Pro/
- MANUS ROS2 SDK guide: https://docs.manus-meta.com/3.1.0/Plugins/SDK/ROS2/getting%20started/
