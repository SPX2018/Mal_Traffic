#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, sys
from pathlib import Path

# 尝试导入 tqdm，失败则提供一个无操作的替代
try:
    from tqdm import tqdm
except Exception:
    def tqdm(iterable=None, total=None, **kwargs):
        return iterable

def find_key(obj, key):
    """在任意嵌套的 dict/list 中递归查找指定 key 的第一个值。"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            got = find_key(v, key)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for it in obj:
            got = find_key(it, key)
            if got is not None:
                return got
    return None

def main():
    ap = argparse.ArgumentParser(description="统计 threat_level=low 的数量与比例（带进度条）")
    ap.add_argument("ROOT", help="根目录（包含多个子目录与JSON结果）")
    ap.add_argument("-p", "--pattern", default="*.json", help="文件匹配模式，默认 *.json")
    args = ap.parse_args()

    root = Path(args.ROOT).resolve()
    if not root.is_dir():
        print(f"ERROR: 目录不存在或不是目录：{root}", file=sys.stderr)
        return 2

    files = list(root.rglob(args.pattern))
    total = len(files)
    if total == 0:
        print("未找到任何 JSON 文件。")
        return 0

    low_cnt = 0
    parse_err = 0
    no_key = 0
    medium_cnt = 0
    high_cnt = 0

    bar = tqdm(files, total=total, desc="扫描JSON", unit="file")
    for f in bar:
        try:
            with f.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            parse_err += 1
            if hasattr(bar, "set_postfix"):
                bar.set_postfix(err=parse_err, no_key=no_key, low=low_cnt)
            continue

        tl = find_key(data, "threat_level")
        if tl is None:
            no_key += 1
        elif isinstance(tl, str) and tl.strip().lower() == "low":
            low_cnt += 1
        elif isinstance(tl, str) and tl.strip().lower() == "medium":
            medium_cnt += 1
        elif isinstance(tl, str) and tl.strip().lower() == "high":
            high_cnt += 1

        if hasattr(bar, "set_postfix"):
            bar.set_postfix(err=parse_err, no_key=no_key, low=low_cnt, medium=medium_cnt, high=high_cnt)

    ratio = low_cnt / total
    print("\n====== 统计结果 ======")
    print(f"总 JSON 文件数: {total}")
    print(f"low 数量     : {low_cnt}")
    print(f"比例         : {ratio:.4f} ({ratio*100:.2f}%)")
    if parse_err or no_key:
        print(f"(提示) 解析失败: {parse_err} 个；缺少 threat_level: {no_key} 个。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
