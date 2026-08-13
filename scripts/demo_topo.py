#!/usr/bin/env python3
"""Launch FRUTool in topology demo mode (no BMC / board swap required)."""
from __future__ import annotations

import argparse
import os
import sys


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FRUTool 拓扑 UI 演示（无需真实 BMC）")
    parser.add_argument(
        "--scenario",
        "-s",
        default=os.environ.get("FRUTOOL_DEMO_SCENARIO", "multi"),
        choices=["multi", "foxconn", "single", "missing"],
        help="演示场景（默认 multi：同套餐多厂商）",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="列出可用场景后退出",
    )
    parser.add_argument(
        "--no-gpu-effects",
        action="store_true",
        help="禁用 GPU 特效（与主程序相同）",
    )
    args, extra = parser.parse_known_args(argv)

    root = _repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    from frutool.demo.topo_demo import list_scenarios

    if args.list_scenarios:
        for item in list_scenarios():
            print(f"{item.key:10} {item.title} — {item.description}")
        return 0

    os.environ.setdefault("FRUTOOL_SKIP_ADMIN", "1")
    os.environ["FRUTOOL_DEMO_TOPO"] = "1"
    os.environ["FRUTOOL_DEMO_SCENARIO"] = args.scenario

    sys.argv = [os.path.join(root, "fru_tool.py")]
    if args.no_gpu_effects:
        sys.argv.append("--no-gpu-effects")
    sys.argv.extend(extra)

    from frutool.main import main as run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
