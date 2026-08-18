#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用法:
  python watch_one_dir.py <INPUT_DIR> <OUTPUT_DIR>

只接收两个参数：数据集目录、报告目录。
脚本会反复运行你的检测程序，直到报告数量与样本数量匹配为止。
环境可通过下方“可调参数(环境变量)”微调，无需改命令行参数。
"""

import os
import sys
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Optional
import importlib.util
import traceback

# ========== 可调参数（通过环境变量覆盖） ==========
# 你的检测脚本路径；默认当前目录下 detect.py
DETECT_SCRIPT = os.getenv("DETECT_SCRIPT", str(Path(__file__).with_name("detect.py")))
DETECT_FUNC   = os.getenv("DETECT_FUNC", "detect")  # detect.py 内部函数名：run(input_dir, output_dir)
RELOAD_EACH_TIME = int(os.getenv("RELOAD_EACH_TIME", "0"))  # 1=每轮热重载 detect.py

# 输入/输出的文件匹配模式（按需改成 *.bin / *.jpg / *.txt / *.json 等）
IN_PATTERN  = os.getenv("IN_PATTERN",  "*.pcap")
OUT_PATTERN = os.getenv("OUT_PATTERN", "*.json")

# 统计是否递归输入目录 (1=递归, 0=仅当前层)
RECURSIVE = int(os.getenv("RECURSIVE", "0"))

# 对比方式：eq=严格相等；ge=报告数>=样本数
COUNT_OP = os.getenv("COUNT_OP", "eq").lower()  # "eq" or "ge"

# 重跑策略
RESTART_DELAY = float(os.getenv("RESTART_DELAY", "3"))  # 不达标重跑的间隔(秒)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "0"))        # 0=无限重试；>0 达到次数即退出
CLEAR_OUTPUT_BEFORE_RUN = int(os.getenv("CLEAR_OUTPUT_BEFORE_RUN", "0"))  # 每次跑前清空输出目录

# “无进展保护”：连续 N 次报告数不增长就退出，避免死循环
STAGNANT_LIMIT = int(os.getenv("STAGNANT_LIMIT", "5"))
# ================================================

def ts() -> str:
    import datetime as _dt
    return _dt.datetime.now().strftime("%F %T")

def echo(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)

def count_files(dir_path: Path, pattern: str, recursive: int) -> int:
    if recursive:
        return sum(1 for _ in dir_path.rglob(pattern))
    else:
        return sum(1 for _ in dir_path.glob(pattern))
# ---- 直接函数调用 ----
_LOADED_MOD = None

def _load_detect_module():
    """按需(热)重载 detect.py 并返回模块对象。"""
    global _LOADED_MOD
    if RELOAD_EACH_TIME or _LOADED_MOD is None:
        spec = importlib.util.spec_from_file_location("user_detect_mod", DETECT_SCRIPT)
        if not spec or not spec.loader:
            raise RuntimeError(f"无法加载模块: {DETECT_SCRIPT}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LOADED_MOD = mod
    return _LOADED_MOD

def call_detect_func(input_dir: Path, output_dir: Path) -> int:
    """调用 detect.py 中的 DETECT_FUNC(input_dir, output_dir)。"""
    mod = _load_detect_module()
    func = getattr(mod, DETECT_FUNC, None)
    if not callable(func):
        raise AttributeError(f"{DETECT_SCRIPT} 未找到可调用函数 '{DETECT_FUNC}'")
    try:
        rv = func(str(input_dir), str(output_dir))
        return 0 if rv is None else int(rv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1



def main() -> int:
    parser = argparse.ArgumentParser(description="监控并重跑检测，直到报告数量达标")
    parser.add_argument("INPUT_DIR", help="数据集目录")
    parser.add_argument("OUTPUT_DIR", help="报告目录")
    args = parser.parse_args()

    input_dir = Path(args.INPUT_DIR).resolve()
    # input_dir = Path('./dataset/ids2019/test/LDAP1').resolve()
    output_dir = Path(args.OUTPUT_DIR).resolve()
    # output_dir = Path('./report/ids2019/test/LDAP1 ').resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        echo(f"ERROR: 输入目录不存在: {input_dir}")
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "fail.txt").touch(exist_ok=True)  # 不计入 *.json

    expected = count_files(input_dir, IN_PATTERN, RECURSIVE)
    echo(f"输入目录: {input_dir}")
    echo(f"预期样本数: {expected} (匹配: {IN_PATTERN}, 递归: {RECURSIVE})")
    echo(f"报告目录: {output_dir} (匹配: {OUT_PATTERN}, 对比方式: {COUNT_OP})")
    echo(f"检测脚本: {DETECT_SCRIPT}  函数: {DETECT_FUNC}  热重载: {RELOAD_EACH_TIME}")

    if expected == 0:
        echo("⚠️ 未找到任何样本，退出。")
        return 0

    attempt = 0
    last_produced: Optional[int] = None
    stagnant = 0

    while True:
        attempt += 1

        if CLEAR_OUTPUT_BEFORE_RUN:
            echo(f"清空输出目录: {output_dir}")
            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "fail.txt").touch(exist_ok=True)

        # —— 仅直接调用 —— #
        try:
            exit_code = call_detect_func(input_dir, output_dir)
        except Exception as e:
            echo(f"函数调用失败: {e!r}")
            echo(traceback.format_exc())
            exit_code = -1

        echo(f"检测函数返回码: {exit_code}")

        produced = count_files(output_dir, OUT_PATTERN, recursive=1)
        echo(f"报告数: {produced} / 预期: {expected}")

        ok = False
        if COUNT_OP == "eq":
            ok = (produced == expected)
        elif COUNT_OP == "ge":
            ok = (produced >= expected)
        else:
            echo(f"WARNING: 未知 COUNT_OP={COUNT_OP!r}，按 eq 处理。")
            ok = (produced == expected)

        if ok:
            echo("✅ 数量达标，完成。")
            return 0

        # 无进展保护
        if last_produced is not None and produced <= last_produced:
            stagnant += 1
        else:
            stagnant = 0
        last_produced = produced

        if MAX_RETRIES > 0 and attempt >= MAX_RETRIES:
            echo(f"❌ 达到最大重试次数({MAX_RETRIES})，退出。")
            return 1
        if stagnant >= STAGNANT_LIMIT:
            echo(f"❌ 连续 {STAGNANT_LIMIT} 次无进展，退出（避免死循环）。")
            return 1

        echo(f"数量不匹配，{RESTART_DELAY}s 后重跑...")
        time.sleep(RESTART_DELAY)

if __name__ == "__main__":
    sys.exit(main())
