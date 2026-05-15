#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Small direct Wuji SDK motion smoke test.")
    parser.add_argument("--serial", default="")
    parser.add_argument("--log-dir", default="/tmp/wuji_sdk_logs")
    parser.add_argument("--finger", type=int, default=1, help="0-based finger index.")
    parser.add_argument("--joint", type=int, default=0, help="0-based joint index.")
    parser.add_argument("--delta", type=float, default=0.08, help="Small radian target offset.")
    parser.add_argument("--hold", type=float, default=0.8)
    parser.add_argument("--disable-on-exit", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    import wujihandpy

    if args.log_dir:
        Path(args.log_dir).expanduser().mkdir(parents=True, exist_ok=True)
        wujihandpy.logging.set_log_path(str(Path(args.log_dir).expanduser().resolve()))

    hand = wujihandpy.Hand(serial_number=args.serial or None)
    lower = np.asarray(hand.read_joint_lower_limit(), dtype=np.float64)
    upper = np.asarray(hand.read_joint_upper_limit(), dtype=np.float64)
    start = np.asarray(hand.read_joint_actual_position(), dtype=np.float64)

    target = start.copy()
    f = int(args.finger)
    j = int(args.joint)
    target[f, j] = np.clip(start[f, j] + float(args.delta), lower[f, j], upper[f, j])

    print(f"start[{f},{j}]={start[f, j]:+.4f} target={target[f, j]:+.4f}")
    hand.write_joint_enabled(True, timeout=0.5)
    try:
        hand.write_joint_target_position(target, timeout=0.5)
        time.sleep(float(args.hold))
        moved = np.asarray(hand.read_joint_actual_position(), dtype=np.float64)
        print(f"moved[{f},{j}]={moved[f, j]:+.4f} delta={moved[f, j] - start[f, j]:+.4f}")
        hand.write_joint_target_position(start, timeout=0.5)
        time.sleep(float(args.hold))
        final = np.asarray(hand.read_joint_actual_position(), dtype=np.float64)
        print(f"final[{f},{j}]={final[f, j]:+.4f} delta={final[f, j] - start[f, j]:+.4f}")
    finally:
        if args.disable_on_exit:
            hand.write_joint_enabled(False, timeout=0.5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
