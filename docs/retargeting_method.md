# Wuji 官方 Retargeting 方法分析

本项目采用 Wuji 官方 `wuji-hand-teleop` 的 MANUS 手套到 Wuji 灵巧手链路。核心算法没有重写，运行时调用的是官方 `wuji_retargeting.Retargeter`。

## 官方链路

```text
manus_ros2/manus_data_publisher
  -> /manus_glove_0, /manus_glove_1
  -> manus_input_py/manus_input
  -> /hand_input
  -> controller/wujihand_controller
  -> wujihand_output.WujiHandController
  -> wuji_retargeting.Retargeter
  -> /{hand_name}/joint_commands
  -> wujihandros2/wujihand_driver_node
```

本仓库保持这个拆分：MANUS 官方 ROS2 publisher 负责读取手套；`manus_input_py` 转换成统一手部输入；`wujihand_controller` 做 retargeting；`wujihandros2` driver 负责真正下发到硬件。

## `/hand_input` 合约

消息类型：

```text
std_msgs/msg/Float32MultiArray
```

数据长度：

```text
单手:  63 floats  = 21 MediaPipe landmarks x xyz
双手: 126 floats  = right hand first, then left hand
```

MediaPipe 21 点顺序：

```text
0      wrist
1-4    thumb
5-8    index
9-12   middle
13-16  ring
17-20  pinky
```

官方 MANUS 固定节点映射：

```text
(1, 22, 23, 24, 25,
 3, 4, 5, 6,
 8, 9, 10, 11,
 13, 14, 15, 16,
 18, 19, 20, 21)
```

官方 `manus_input_py` 在发布前对 Y 轴取反，使 MANUS 原始骨架坐标进入官方约定的 MediaPipe 坐标。

## 官方 API 调用

Wuji 官方 retargeting API 是：

```python
from wuji_retargeting import Retargeter

retargeter = Retargeter.from_yaml("retarget_manus_right.yaml", "right")
qpos = retargeter.retarget(raw_keypoints)
```

输入：

- `raw_keypoints`: `numpy.ndarray`, shape `(21, 3)`
- 顺序：MediaPipe hand landmarks
- 单位：米

输出：

- `qpos`: `numpy.ndarray`, shape `(20,)`
- 单位：弧度
- 顺序：thumb, index, middle, ring, pinky，每指 4 个关节

## 坐标处理

`Retargeter.retarget()` 的处理流程：

```text
raw MediaPipe keypoints
  -> wrist-local normalization
  -> 用 wrist / index MCP / middle MCP 构建手腕坐标系
  -> 按 right/left 应用 OPERATOR2MANO transform
  -> 应用 YAML 中 mediapipe_rotation
  -> 送入优化器
```

官方 MANUS 配置：

```yaml
# right hand
mediapipe_rotation:
  x: 0.0
  y: 0.0
  z: -15.0

# left hand
mediapipe_rotation:
  x: 0.0
  y: 0.0
  z: 15.0
```

## 优化器

官方 MANUS 配置使用：

```yaml
optimizer:
  type: "AdaptiveOptimizerAnalytical"
```

求解流程：

```text
MediaPipe 21 keypoints
  -> 构造目标向量
  -> Wuji URDF forward kinematics
  -> NLopt SLSQP 优化 20 个关节角
  -> joint limit bounds
  -> 用上一帧 qpos warm start
  -> low-pass filter 平滑输出
```

配置中的 `huber_delta`、`huber_delta_dir`、`pinch_thresholds` 等距离量按厘米解释。

## Adaptive Loss

官方方法按每个非拇指手指在两类目标之间自适应切换：

- `TipDirVec`：强调 fingertip 位置和 fingertip 方向，适合捏合/接触附近。
- `FullHandVec`：强调 PIP/DIP/TIP 相对 wrist 的整指形态，适合自然弯曲。

混合规则：

```text
d < d1: TipDirVec
d > d2: FullHandVec
d1..d2: 线性插值
```

官方右手阈值：

```yaml
pinch_thresholds:
  index:  { d1: 2.0, d2: 4.0 }
  middle: { d1: 2.0, d2: 4.0 }
  ring:   { d1: 2.0, d2: 4.0 }
  pinky:  { d1: 2.0, d2: 4.0 }
```

损失形式：

```text
L = sum_i alpha_i * L_tip_dir_vec_i
  + sum_i (1 - alpha_i) * L_full_hand_i
  + norm_delta * ||qpos - last_qpos||^2
```

实现使用 Huber loss 和解析梯度。

## 滤波

官方 MANUS 配置：

```yaml
lp_alpha: 0.3
```

滤波形式：

```text
y_t = y_{t-1} + lp_alpha * (qpos_t - y_{t-1})
```

## 本仓库与官方方法的差异

完全一致的部分：

- `wuji-hand-teleop/src/controller/controller/wujihand_node.py`
- `wuji-hand-teleop/src/output_devices/wujihand_output/wujihand_output/wujihand_controller.py`
- `wuji-hand-teleop/src/output_devices/wujihand_output/wujihand_output/_internal/hand_interface.py`
- `third_party/wuji_official/wuji_retargeting`
- 官方 `retarget_manus_right.yaml`
- 官方 `wujihandros2` driver

本仓库增加的封装：

- `launch/manus_wuji_right.launch.py`：只启动单右手 `/hand_0`，保留官方节点和话题。
- `config/manus_input_right_only.yaml`：只发布右手 63 floats。
- `config/wujihand_ik_right_hand0.yaml`：只启用右手 namespace `hand_0`。
- `scripts/*`：环境、构建、udev、设备检查、启动和停止脚本。

唯一输入兼容补丁：

```text
wuji-hand-teleop/src/input_devices/manus_input/manus_input_py/manus_input_py/manus_input_node.py
```

部分 MANUS ROS2 publisher 会发布语义节点 `chain_type/joint_type`，节点 id 是 `0..24`；官方样例期望固定 id `(1, 22, 23, 24, 25, ...)`。补丁逻辑是：

1. 先尝试官方固定 id 映射。
2. 如果固定 id 缺失，则按 `Hand/Thumb/Index/Middle/Ring/Pinky` 和 `MCP/PIP/DIP/TIP` 语义恢复 MediaPipe 21 点顺序。
3. 输出仍是同一个 `/hand_input` 合约。

这个补丁不改变 retargeting、优化器、滤波、Wuji driver 或输出关节角。

## 官方资料

- Wuji hand teleop: https://github.com/wuji-technology/wuji-hand-teleop
- Wuji retargeting API: https://docs.wuji.tech/docs/zh/wuji-hand/latest/retargeting/api/
- Wuji ROS2 interface: https://docs.wuji.tech/docs/zh/wuji-hand/latest/ros2-user-guide/ros2-interface/
