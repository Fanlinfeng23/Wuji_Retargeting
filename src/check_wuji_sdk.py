#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read basic state from a USB-connected Wuji hand.")
    parser.add_argument("--serial", default="", help="Optional Wuji hand serial number.")
    parser.add_argument("--log-dir", default="/tmp/wuji_sdk_logs")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    import wujihandpy

    if args.log_dir:
        Path(args.log_dir).expanduser().mkdir(parents=True, exist_ok=True)
        wujihandpy.logging.set_log_path(str(Path(args.log_dir).expanduser().resolve()))

    hand = wujihandpy.Hand(serial_number=args.serial or None)
    pos = np.asarray(hand.read_joint_actual_position(), dtype=np.float64)
    lower = np.asarray(hand.read_joint_lower_limit(), dtype=np.float64)
    upper = np.asarray(hand.read_joint_upper_limit(), dtype=np.float64)

    print(f"wujihandpy={wujihandpy.__version__}")
    print(f"handedness={int(hand.read_handedness())}")
    print(f"firmware_version={int(hand.read_firmware_version())}")
    print(f"input_voltage={float(hand.read_input_voltage()):.3f} V")
    print(f"joint_shape={pos.shape}")
    print(f"joint_range=[{pos.min():+.4f}, {pos.max():+.4f}]")
    print(f"limit_range=[{lower.min():+.4f}, {upper.max():+.4f}]")
    print("first_8_positions=" + ", ".join(f"{v:+.4f}" for v in pos.reshape(-1)[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
