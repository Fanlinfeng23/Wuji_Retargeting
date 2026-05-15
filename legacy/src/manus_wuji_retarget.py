#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import argparse
import atexit
import sys
import time
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
WUJI_OFFICIAL_ROOT = PROJECT_ROOT / "third_party" / "wuji_official"
WUJI_RETARGETING_SRC = WUJI_OFFICIAL_ROOT

if str(WUJI_RETARGETING_SRC) not in sys.path:
    sys.path.insert(0, str(WUJI_RETARGETING_SRC))

from wuji_retargeting import Retargeter


DEFAULT_RIGHT_CONFIG_PATH = WUJI_OFFICIAL_ROOT / "config" / "retarget_manus_right.yaml"
DEFAULT_LEFT_CONFIG_PATH = WUJI_OFFICIAL_ROOT / "config" / "retarget_manus_left.yaml"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "examples" / "manus_data.npy"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "manus_wuji_retargeting.npz"

OFFICIAL_SOURCE_REFS = [
    "https://github.com/wuji-technology/wuji-retargeting/tree/430772f20e34dee0704ec731bcf7535935c9e082",
    "https://github.com/wuji-technology/wuji-hand-teleop/tree/3fa58481e971bf1588b57751ea44d99abe1d95b5",
    "https://docs.wuji.tech/docs/zh/wuji-hand/latest/retargeting/",
]

# Official wuji-hand-teleop Manus input mapping:
# src/input_devices/manus_input/manus_input_py/manus_input_py/manus_input_node.py
OFFICIAL_MEDIAPIPE_TO_MANUS = (
    1, 22, 23, 24, 25,  # WRIST + THUMB
    3, 4, 5, 6,         # INDEX
    8, 9, 10, 11,       # MIDDLE
    13, 14, 15, 16,     # RING
    18, 19, 20, 21,     # PINKY
)
SEMANTIC_CHAIN_NAMES = ("Thumb", "Index", "Middle", "Ring", "Pinky")

WUJI_JOINT_NAMES = [
    "thumb_joint_0", "thumb_joint_1", "thumb_joint_2", "thumb_joint_3",
    "index_joint_0", "index_joint_1", "index_joint_2", "index_joint_3",
    "middle_joint_0", "middle_joint_1", "middle_joint_2", "middle_joint_3",
    "ring_joint_0", "ring_joint_1", "ring_joint_2", "ring_joint_3",
    "pinky_joint_0", "pinky_joint_1", "pinky_joint_2", "pinky_joint_3",
]


def _node_position(node, flip_y: bool = True) -> np.ndarray:
    pos = node.pose.position
    y = -pos.y if flip_y else pos.y
    return np.array([pos.x, y, pos.z], dtype=np.float32)


def _order_chain_nodes_by_joint_type(nodes) -> list:
    by_type = {}
    for node in nodes:
        by_type.setdefault(node.joint_type, []).append(node)

    def pick(*joint_types):
        for joint_type in joint_types:
            candidates = by_type.get(joint_type, [])
            if candidates:
                return min(candidates, key=lambda node: node.node_id)
        return None

    ordered = [
        pick("MCP"),
        pick("PIP"),
        pick("DIP", "IP"),
        pick("TIP"),
    ]
    if all(node is not None for node in ordered):
        return ordered

    priority = {"MCP": 0, "PIP": 1, "IP": 2, "DIP": 2, "TIP": 3}
    typed = [node for node in nodes if node.joint_type in priority]
    if len(typed) >= 4:
        return sorted(typed, key=lambda node: (priority[node.joint_type], node.node_id))[-4:]

    return []


def _order_chain_nodes(nodes) -> list:
    if len(nodes) == 0:
        return []

    ordered_by_joint_type = _order_chain_nodes_by_joint_type(nodes)
    if len(ordered_by_joint_type) >= 4:
        return ordered_by_joint_type

    node_by_id = {node.node_id: node for node in nodes}
    child_map = {}
    root = None

    for node in nodes:
        if node.parent_node_id in node_by_id:
            child_map.setdefault(node.parent_node_id, []).append(node)
        else:
            root = node

    if root is None:
        root = min(nodes, key=lambda node: node.node_id)

    ordered = []
    current = root
    visited = set()
    while current is not None and current.node_id not in visited:
        ordered.append(current)
        visited.add(current.node_id)
        children = sorted(child_map.get(current.node_id, []), key=lambda node: node.node_id)
        current = children[0] if len(children) > 0 else None

    return ordered


def _select_mediapipe_finger_nodes(nodes) -> list:
    ordered = _order_chain_nodes(nodes)
    if len(ordered) == 4:
        return ordered
    if len(ordered) >= 5:
        return [ordered[0], ordered[1], ordered[-2], ordered[-1]]
    return []


def _raw_nodes_to_semantic_mediapipe(raw_nodes, flip_y: bool = True) -> np.ndarray:
    hand_nodes = [node for node in raw_nodes if node.chain_type == "Hand"]
    if len(hand_nodes) == 0:
        raise ValueError("Missing Manus hand root node required by semantic MediaPipe mapping.")

    wrist = min(hand_nodes, key=lambda node: node.node_id)
    mediapipe_pose = [_node_position(wrist, flip_y=flip_y)]
    incomplete = []

    for chain_name in SEMANTIC_CHAIN_NAMES:
        chain_nodes = [node for node in raw_nodes if node.chain_type == chain_name]
        finger_nodes = _select_mediapipe_finger_nodes(chain_nodes)
        if len(finger_nodes) != 4:
            incomplete.append(chain_name)
            continue
        mediapipe_pose.extend(_node_position(node, flip_y=flip_y) for node in finger_nodes)

    if incomplete:
        raise ValueError(
            "Missing Manus semantic chain(s) required by fallback MediaPipe mapping: "
            f"{incomplete}"
        )

    mediapipe_pose = np.asarray(mediapipe_pose, dtype=np.float32)
    if mediapipe_pose.shape != (21, 3):
        raise ValueError(f"Semantic MediaPipe mapping produced shape {mediapipe_pose.shape}")
    return mediapipe_pose


def raw_nodes_to_wuji_mediapipe(raw_nodes, flip_y: bool = True) -> np.ndarray:
    """Convert Manus raw_nodes to the official Wuji MediaPipe (21, 3) input.

    This intentionally mirrors wuji-hand-teleop's ManusInputNode:
    fixed Manus node_id mapping plus Y-axis flip. It does not use the older
    older project-specific canonical wrist frame. Some Manus SDK versions publish semantic
    chain node IDs (for example 0-24) instead of Wuji's fixed example IDs, so
    this falls back to chain_type/joint_type ordering when fixed IDs are absent.
    """
    positions = {int(node.node_id): _node_position(node, flip_y=flip_y) for node in raw_nodes}
    mediapipe_pose = np.zeros((21, 3), dtype=np.float32)
    missing = []

    for mp_idx, manus_node_id in enumerate(OFFICIAL_MEDIAPIPE_TO_MANUS):
        point = positions.get(manus_node_id)
        if point is None:
            missing.append(manus_node_id)
        else:
            mediapipe_pose[mp_idx] = point

    if missing:
        return _raw_nodes_to_semantic_mediapipe(raw_nodes, flip_y=flip_y)
    return mediapipe_pose


def _is_valid_keypoints(keypoints: np.ndarray, eps: float = 1e-6) -> bool:
    keypoints = np.asarray(keypoints)
    if keypoints.shape != (21, 3):
        return False
    if not np.isfinite(keypoints).all():
        return False
    wrist = keypoints[0]
    max_radius = np.max(np.linalg.norm(keypoints - wrist, axis=1))
    return np.isfinite(max_radius) and max_radius > eps


def _geort_dex_to_wuji_mediapipe(points: np.ndarray) -> np.ndarray:
    """Best-effort conversion for existing project-specific canonical recordings.

    Live ROS uses Wuji's official raw_nodes -> MediaPipe conversion. Existing
    .npy files in this format are already wrist-local MANO/dex-style data, so
    offline replay can pass them to Wuji Retargeter after undoing the known
    OPERATOR2MANO_RIGHT axis permutation. No official Wuji document defines
    this .npy format as an input format, so this mode is for local regression only.
    """
    return np.asarray(points, dtype=np.float32)


def prepare_npy_frame(frame: np.ndarray, npy_frame: str) -> np.ndarray:
    frame = np.asarray(frame, dtype=np.float32)
    if npy_frame == "wuji":
        return frame
    if npy_frame in {"dex", "geort"}:
        return _geort_dex_to_wuji_mediapipe(frame)
    raise ValueError(f"Unsupported --npy-frame value: {npy_frame}")


def _resolve_config_path(hand: str, config_path: str) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()
    if hand == "left":
        return DEFAULT_LEFT_CONFIG_PATH.resolve()
    return DEFAULT_RIGHT_CONFIG_PATH.resolve()


def build_retargeter(hand: str, config_path: str) -> Retargeter:
    resolved = _resolve_config_path(hand, config_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"Wuji retarget config not found: {resolved}. "
            "Use --config to point at official retarget_manus_right/left.yaml."
        )
    return Retargeter.from_yaml(str(resolved), hand)


def retarget_frame(
    retargeter: Retargeter,
    keypoints: np.ndarray,
    apply_filter: bool,
    verbose: bool = False,
) -> tuple[np.ndarray, dict]:
    keypoints = np.asarray(keypoints, dtype=np.float32)
    if keypoints.shape != (21, 3):
        raise ValueError(f"Expected (21, 3) MediaPipe keypoints, got {keypoints.shape}")
    if verbose:
        qpos, details = retargeter.retarget_verbose(keypoints, apply_filter=apply_filter)
        return np.asarray(qpos, dtype=np.float32), details
    qpos = retargeter.retarget(keypoints, apply_filter=apply_filter)
    return np.asarray(qpos, dtype=np.float32), {}


def clip_to_retarget_limits(retargeter: Retargeter, qpos: np.ndarray) -> np.ndarray:
    qpos = np.asarray(qpos, dtype=np.float32)
    limits = getattr(retargeter.optimizer.robot, "joint_limits", None)
    if limits is None:
        return qpos
    limits = np.asarray(limits, dtype=np.float32)
    if limits.shape != (qpos.size, 2):
        return qpos
    return np.clip(qpos, limits[:, 0], limits[:, 1]).astype(np.float32)


def summarize_vector(values: Sequence[float], names: Sequence[str], count: int = 6) -> str:
    return ", ".join(f"{name}={float(value):+.3f}" for name, value in zip(names[:count], values[:count]))


def get_ros_qos(depth: int = 1, reliable: bool = False):
    from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE if reliable else ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=depth,
    )


def default_publish_topic(output_mode: str, hand: str, hand_name: str) -> str:
    if output_mode == "hand-input":
        return "/hand_input"
    if output_mode == "joint-command":
        return f"/wuji_hand/{hand}/joint_command"
    if hand_name:
        return f"/{hand_name}/joint_commands"
    return "/hand_0/joint_commands"


def _split_hand_input_payload(raw: np.ndarray, hand: str) -> np.ndarray:
    raw = np.asarray(raw, dtype=np.float32)
    if raw.size == 63:
        return raw.reshape(21, 3)
    if raw.size == 126:
        if hand == "right":
            return raw[:63].reshape(21, 3)
        return raw[63:].reshape(21, 3)
    raise ValueError(f"Expected /hand_input with 63 or 126 floats, got {raw.size}")


def _as_sdk_joint_matrix(qpos: np.ndarray) -> np.ndarray:
    qpos = np.asarray(qpos, dtype=np.float64)
    if qpos.shape == (5, 4):
        return qpos
    if qpos.size != 20:
        raise ValueError(f"Expected 20 Wuji joint values, got shape {qpos.shape}")
    return qpos.reshape(5, 4)


class WujiSdkController:
    """Thin runtime wrapper around the official wujihandpy SDK.

    The SDK exposes 5x4 joint arrays, while the retargeter returns the same
    order flattened: thumb, index, middle, ring, pinky, four joints each.
    """

    def __init__(self, args: argparse.Namespace):
        import wujihandpy

        if args.sdk_log_dir:
            Path(args.sdk_log_dir).expanduser().mkdir(parents=True, exist_ok=True)
            wujihandpy.logging.set_log_path(str(Path(args.sdk_log_dir).expanduser().resolve()))
        if args.sdk_quiet:
            wujihandpy.logging.set_log_to_console(False)

        self.wujihandpy = wujihandpy
        self.hand = wujihandpy.Hand(serial_number=args.sdk_serial or None)
        self.lower = np.asarray(self.hand.read_joint_lower_limit(), dtype=np.float64)
        self.upper = np.asarray(self.hand.read_joint_upper_limit(), dtype=np.float64)
        self.current = np.asarray(self.hand.read_joint_actual_position(), dtype=np.float64)
        self.enabled = bool(args.sdk_enable)
        if self.enabled:
            self.hand.write_joint_enabled(True, timeout=0.5)
        self.use_realtime = bool(args.sdk_realtime)
        if self.use_realtime:
            self.controller = self.hand.realtime_controller(
                bool(args.sdk_enable_upstream),
                wujihandpy.filter.LowPass(float(args.sdk_cutoff_hz)),
            )
            atexit.register(self.close)
        else:
            self.controller = None

    def close(self):
        controller = getattr(self, "controller", None)
        if controller is not None:
            try:
                controller.close()
            except Exception:
                pass
            self.controller = None
        if getattr(self, "enabled", False):
            try:
                self.hand.write_joint_enabled(False, timeout=0.5)
            except Exception:
                pass
            self.enabled = False

    def limits_text(self) -> str:
        return (
            f"current=[{self.current.min():+.3f}, {self.current.max():+.3f}] "
            f"lower=[{self.lower.min():+.3f}, {self.lower.max():+.3f}] "
            f"upper=[{self.upper.min():+.3f}, {self.upper.max():+.3f}]"
        )

    def command(self, qpos: np.ndarray, blend: float = 1.0) -> np.ndarray:
        target = _as_sdk_joint_matrix(qpos)
        target = np.clip(target, self.lower, self.upper)
        if blend < 1.0:
            target = self.current + float(blend) * (target - self.current)
            target = np.clip(target, self.lower, self.upper)
        if self.controller is not None:
            self.controller.set_joint_target_position(target)
        else:
            self.hand.write_joint_target_position(target, timeout=0.2)
        return target.reshape(-1).astype(np.float32)


def run_offline(args: argparse.Namespace) -> int:
    input_path = Path(args.npy_path).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve() if args.output_path else None
    data = np.load(input_path)
    if data.ndim != 3 or data.shape[1:] != (21, 3):
        raise ValueError(f"Expected (N, 21, 3) data, got {data.shape}")

    retargeter = build_retargeter(args.hand, args.config)
    max_frames = args.max_frames if args.max_frames and args.max_frames > 0 else len(data)
    apply_filter = not args.no_filter

    qpos_frames = []
    input_frames = []
    transformed_frames = []
    costs = []
    processed = 0
    tic = time.perf_counter()

    for frame_idx, frame in enumerate(data[:max_frames]):
        if not _is_valid_keypoints(frame):
            continue
        keypoints = prepare_npy_frame(frame, args.npy_frame)
        if not _is_valid_keypoints(keypoints):
            continue
        qpos, verbose = retarget_frame(retargeter, keypoints, apply_filter=apply_filter, verbose=True)
        qpos_frames.append(qpos)
        input_frames.append(keypoints)
        transformed_frames.append(verbose["mediapipe_kp"].astype(np.float32))
        costs.append(float(verbose.get("cost", 0.0)))
        processed += 1
        if args.print_every > 0 and processed % args.print_every == 0:
            print(
                f"[wuji-offline] frame={frame_idx + 1} processed={processed} "
                f"qpos: {summarize_vector(qpos, WUJI_JOINT_NAMES)} cost={costs[-1]:.4f}"
            )

    if not qpos_frames:
        raise RuntimeError("No valid frames were retargeted.")

    qpos_frames = np.asarray(qpos_frames, dtype=np.float32)
    input_frames = np.asarray(input_frames, dtype=np.float32)
    transformed_frames = np.asarray(transformed_frames, dtype=np.float32)
    costs = np.asarray(costs, dtype=np.float32)

    wall_time = time.perf_counter() - tic
    print(
        f"[wuji-offline] valid_frames={len(qpos_frames)} total_frames={min(len(data), max_frames)} "
        f"wall_time_s={wall_time:.3f}"
    )
    print(
        f"[wuji-offline] qpos range=[{qpos_frames.min():+.4f}, {qpos_frames.max():+.4f}] "
        f"cost range=[{costs.min():.4f}, {costs.max():.4f}]"
    )
    print(f"[wuji-offline] first qpos: {summarize_vector(qpos_frames[0], WUJI_JOINT_NAMES, count=8)}")
    print(f"[wuji-offline] official robot joint order: {retargeter.optimizer.robot.dof_joint_names}")

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            output_path,
            qpos_wuji=qpos_frames,
            wuji_command_names=np.asarray(WUJI_JOINT_NAMES),
            wuji_robot_joint_names=np.asarray(retargeter.optimizer.robot.dof_joint_names),
            input_mediapipe=input_frames,
            transformed_mediapipe=transformed_frames,
            cost=costs,
            hand=np.asarray([args.hand]),
            npy_frame=np.asarray([args.npy_frame]),
            config_path=np.asarray([str(_resolve_config_path(args.hand, args.config))]),
            input_path=np.asarray([str(input_path)]),
            official_source_refs=np.asarray(OFFICIAL_SOURCE_REFS),
        )
        print(f"[wuji-offline] saved to {output_path}")

    return 0


def run_ros(args: argparse.Namespace) -> int:
    import rclpy
    from manus_ros2_msgs.msg import ManusGlove
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Float32MultiArray

    class ManusWujiRetargetNode(Node):
        def __init__(self):
            super().__init__("manus_wuji_retarget")
            self.hand = args.hand
            self.output_mode = args.output_mode
            self.print_every = max(1, args.print_every)
            self.processed = 0
            self.skipped = 0
            self.apply_filter = not args.no_filter
            self.log_cost = bool(args.log_cost)
            self.max_runtime_s = float(args.max_runtime_s)
            self.stop_time = time.monotonic() + self.max_runtime_s if self.max_runtime_s > 0 else None
            self.should_stop = False
            self.runtime_timer = None
            if self.stop_time is not None:
                self.runtime_timer = self.create_timer(0.1, self.check_runtime)
            self.retargeter = None
            if self.output_mode != "hand-input":
                self.retargeter = build_retargeter(self.hand, args.config)
            self.sdk_controller = None
            if self.output_mode == "sdk":
                self.sdk_controller = WujiSdkController(args)

            output_qos = get_ros_qos(args.qos_depth, reliable=False)
            input_qos = get_ros_qos(args.qos_depth, reliable=not args.manus_best_effort)
            hand_name = args.hand_name or f"{self.hand}_hand"
            publish_topic = args.publish_topic or default_publish_topic(
                self.output_mode, self.hand, hand_name
            )
            if self.output_mode == "hand-input":
                self.publisher = self.create_publisher(Float32MultiArray, publish_topic, output_qos)
            elif self.output_mode == "sdk":
                self.publisher = None
            else:
                self.publisher = self.create_publisher(JointState, publish_topic, output_qos)

            if args.ros_input_topic:
                input_topic = args.ros_input_topic
            elif args.ros_source == "hand-input":
                input_topic = "/hand_input"
            else:
                input_topic = f"/manus_glove_{args.glove_id}"

            if args.ros_source == "hand-input":
                self.subscription = self.create_subscription(
                    Float32MultiArray, input_topic, self.hand_input_callback, input_qos
                )
            else:
                self.subscription = self.create_subscription(
                    ManusGlove, input_topic, self.glove_callback, input_qos
                )

            config_text = "none" if self.retargeter is None else str(_resolve_config_path(self.hand, args.config))
            publish_text = "wujihandpy SDK" if self.output_mode == "sdk" else publish_topic
            self.get_logger().info(
                f"Listening on {input_topic}, publishing {publish_text}, "
                f"ros_source={args.ros_source}, output_mode={self.output_mode}, "
                f"hand={self.hand}, config={config_text}"
            )
            if self.sdk_controller is not None:
                self.get_logger().info(f"Wuji SDK connected: {self.sdk_controller.limits_text()}")

        def check_runtime(self):
            if self.stop_time is not None and time.monotonic() >= self.stop_time:
                self.get_logger().info(f"Reached --max-runtime-s={self.max_runtime_s:.2f}; shutting down.")
                self.should_stop = True

        def publish_hand_input(self, keypoints: np.ndarray):
            msg = Float32MultiArray()
            msg.data = np.asarray(keypoints, dtype=np.float32).reshape(-1).tolist()
            self.publisher.publish(msg)

        def publish_joint_state(self, qpos: np.ndarray):
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = args.frame_id or f"{self.hand}_hand"
            if self.output_mode == "driver":
                # wujihandros2 accepts position-only arrays in thumb,index,middle,ring,pinky order.
                # Non-official names are ignored by the driver, so keep this empty for hardware commands.
                msg.name = []
            else:
                msg.name = list(WUJI_JOINT_NAMES)
            msg.position = np.asarray(qpos, dtype=np.float64).tolist()
            self.publisher.publish(msg)

        def handle_keypoints(self, keypoints: np.ndarray):
            if not _is_valid_keypoints(keypoints):
                self.skipped += 1
                return

            if self.output_mode == "hand-input":
                self.publish_hand_input(keypoints)
                qpos = None
                cost = 0.0
            else:
                try:
                    qpos, verbose = retarget_frame(
                        self.retargeter,
                        keypoints,
                        self.apply_filter,
                        verbose=self.log_cost,
                    )
                except Exception as exc:
                    self.skipped += 1
                    self.get_logger().warn(f"Wuji Retargeter failed: {exc}")
                    return
                if self.output_mode == "sdk":
                    qpos = self.sdk_controller.command(qpos, blend=args.sdk_command_blend)
                else:
                    qpos = clip_to_retarget_limits(self.retargeter, qpos)
                    self.publish_joint_state(qpos)
                cost = float(verbose["cost"]) if self.log_cost and "cost" in verbose else None

            self.processed += 1
            if self.processed % self.print_every == 0:
                if qpos is None:
                    summary = "published MediaPipe 21x3 to official /hand_input format"
                else:
                    summary = f"qpos: {summarize_vector(qpos, WUJI_JOINT_NAMES)}"
                    if cost is not None:
                        summary += f" cost={cost:.4f}"
                self.get_logger().info(
                    f"processed={self.processed} skipped={self.skipped} {summary}"
                )
            self.check_runtime()

        def glove_callback(self, msg: ManusGlove):
            if args.require_side and msg.side and msg.side.lower() != self.hand:
                self.skipped += 1
                return
            try:
                keypoints = raw_nodes_to_wuji_mediapipe(msg.raw_nodes, flip_y=not args.no_flip_y)
            except ValueError as exc:
                self.skipped += 1
                self.get_logger().warn(str(exc))
                return
            self.handle_keypoints(keypoints)

        def hand_input_callback(self, msg: Float32MultiArray):
            try:
                keypoints = _split_hand_input_payload(np.asarray(msg.data, dtype=np.float32), self.hand)
            except ValueError as exc:
                self.skipped += 1
                self.get_logger().warn(str(exc))
                return
            if self.output_mode == "hand-input":
                # Avoid republishing to the same official topic and creating a loop.
                self.skipped += 1
                return
            self.handle_keypoints(keypoints)

    rclpy.init()
    node = None
    node = ManusWujiRetargetNode()
    try:
        while rclpy.ok() and not node.should_stop:
            rclpy.spin_once(node, timeout_sec=0.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None and getattr(node, "sdk_controller", None) is not None:
            node.sdk_controller.close()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Retarget Manus glove data to Wuji Hand using Wuji's official Retargeter."
    )
    parser.add_argument("--input", choices=["npy", "ros"], required=True)
    parser.add_argument("--hand", choices=["right", "left"], default="right")
    parser.add_argument("--config", default="")
    parser.add_argument("--print-every", type=int, default=120)
    parser.add_argument("--no-filter", action="store_true", help="Disable Wuji Retargeter low-pass filter.")
    parser.add_argument(
        "--log-cost",
        action="store_true",
        help="Use Retargeter.retarget_verbose() in ROS mode to log optimization cost. Default uses official Retargeter.retarget().",
    )

    parser.add_argument("--npy-path", default=str(DEFAULT_INPUT_PATH))
    parser.add_argument(
        "--npy-frame",
        choices=["wuji", "dex", "geort"],
        default="dex",
        help="wuji means official MediaPipe input; dex/geort means legacy wrist-local canonical recordings.",
    )
    parser.add_argument("--output-path", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--max-frames", type=int, default=0)

    parser.add_argument("--ros-source", choices=["manus-glove", "hand-input"], default="manus-glove")
    parser.add_argument("--ros-input-topic", default="")
    parser.add_argument("--glove-id", type=int, default=0)
    parser.add_argument(
        "--output-mode",
        choices=["driver", "joint-command", "hand-input", "sdk"],
        default="driver",
        help=(
            "driver publishes to /<hand_name>/joint_commands for wujihandros2; "
            "joint-command publishes debug/controller JointState; hand-input publishes official /hand_input; "
            "sdk controls a USB-connected Wuji hand through wujihandpy."
        ),
    )
    parser.add_argument("--publish-topic", default="")
    parser.add_argument("--hand-name", default="")
    parser.add_argument("--frame-id", default="")
    parser.add_argument("--no-flip-y", action="store_true")
    parser.add_argument("--require-side", action="store_true")
    parser.add_argument(
        "--qos-depth",
        type=int,
        default=1,
        help="ROS QoS KEEP_LAST depth. Wuji command output uses SensorDataQoS-style depth=1.",
    )
    parser.add_argument(
        "--manus-best-effort",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Subscribe to Manus input with BEST_EFFORT, matching Wuji official teleop. Use --no-manus-best-effort for local compatibility.",
    )
    parser.add_argument(
        "--max-runtime-s",
        type=float,
        default=0.0,
        help="Stop ROS mode after this many seconds. 0 means run until interrupted.",
    )

    parser.add_argument("--sdk-serial", default="", help="Optional Wuji hand serial number for wujihandpy.Hand.")
    parser.add_argument(
        "--sdk-enable",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable Wuji joints before sending targets and disable them on exit.",
    )
    parser.add_argument("--sdk-log-dir", default="/tmp/wuji_sdk_logs")
    parser.add_argument("--sdk-quiet", action="store_true", help="Disable Wuji SDK console logging.")
    parser.add_argument(
        "--sdk-cutoff-hz",
        type=float,
        default=10.0,
        help="Cutoff frequency for Wuji SDK realtime_controller LowPass filter.",
    )
    parser.add_argument(
        "--sdk-enable-upstream",
        action="store_true",
        help="Enable upstream state in the SDK realtime controller.",
    )
    parser.add_argument(
        "--sdk-realtime",
        action="store_true",
        help="Use Wuji SDK realtime_controller. Default uses bounded synchronous writes for clean shutdown.",
    )
    parser.add_argument(
        "--sdk-command-blend",
        type=float,
        default=1.0,
        help="Blend first-level command toward retargeted qpos from current hand pose; use <1 for smoke tests.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.input == "npy":
        return run_offline(args)
    return run_ros(args)


if __name__ == "__main__":
    raise SystemExit(main())
