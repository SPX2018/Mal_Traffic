#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, sys, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict

# 优先 orjson，加速
try:
    import orjson as _json


    def json_loads(b: bytes):
        return _json.loads(b)
except Exception:
    import json as _json


    def json_loads(b: bytes):
        return _json.loads(b.decode("utf-8", errors="replace"))

try:
    from tqdm import tqdm
except Exception:
    def tqdm(iterable=None, total=None, **kwargs):
        return iterable


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj: return obj[key]
        for v in obj.values():
            got = find_key(v, key)
            if got is not None: return got
    elif isinstance(obj, list):
        for it in obj:
            got = find_key(it, key)
            if got is not None: return got
    return None


_rx_level = re.compile(rb'"threat_level"\s*:\s*"(low|medium|high)"', re.IGNORECASE)
_rx_has_key = re.compile(rb'"threat_level"\s*:', re.IGNORECASE)
_rx_category = re.compile(r'^([a-zA-Z_\-]+?)(\d*)$')


def extract_category(folder_name):
    m = _rx_category.match(folder_name)
    if m: return m.group(1)
    return folder_name


def worker_regex(path: Path):
    try:
        b = path.read_bytes()
    except Exception:
        return (0, 0, 0, 0, 0)
    m = _rx_level.search(b)
    if m:
        val = m.group(1).decode().lower()
        if val == "low":    return (1, 0, 0, 1, 1)
        if val == "medium": return (0, 1, 0, 1, 1)
        return (0, 0, 1, 1, 1)
    return (0, 0, 0, 1 if _rx_has_key.search(b) else 0, 1)


def worker_json(path: Path):
    try:
        b = path.read_bytes()
        data = json_loads(b)
    except Exception:
        return (0, 0, 0, 0, 0)
    v = find_key(data, "threat_level")
    if v is None: return (0, 0, 0, 0, 1)
    try:
        s = str(v).strip().lower()
    except Exception:
        s = ""
    if s == "low":    return (1, 0, 0, 1, 1)
    if s == "medium": return (0, 1, 0, 1, 1)
    if s == "high":   return (0, 0, 1, 1, 1)
    return (0, 0, 0, 1, 1)


def main():
    ap = argparse.ArgumentParser(description="统计脚本（合并High+Med，并统计有效识别总数）")
    ap.add_argument("ROOT", help="原始全量报告的根目录")
    ap.add_argument("-r", "--recheck", help="复检报告的目录")
    ap.add_argument("-p", "--pattern", default="*.json", help="默认 *.json")
    ap.add_argument("-j", "--jobs", type=int, default=0, help="并发数")
    ap.add_argument("--regex-fast", action="store_true", help="极速模式")
    ap.add_argument("-b", "--bengin", type=bool, default=False, help="过滤模式")
    args = ap.parse_args()

    root = Path(args.ROOT).resolve()
    files = [p for p in root.rglob(args.pattern) if p.is_file()]
    if args.bengin:
        files = [p for p in files if "benign" in p.as_posix()]
    else:
        files = [p for p in files if "benign" not in p.as_posix()]

    total = len(files)
    print(f"原始文件总数: {total}")

    recheck_map = {}
    if args.recheck:
        recheck_root = Path(args.recheck).resolve()
        print(f"正在扫描复检目录: {recheck_root}")
        for p in recheck_root.rglob("*.json"):
            recheck_map[p.name] = p
        print(f"复检目录中包含 {len(recheck_map)} 个新报告。")
    else:
        print("未指定 -r 参数，仅统计原始文件。")

    worker = worker_regex if args.regex_fast else worker_json
    jobs = args.jobs or None

    category_stats = defaultdict(
        lambda: {'low': 0, 'medium': 0, 'high': 0, 'err': 0, 'no_key': 0, 'total': 0, 'patched': 0})

    with ProcessPoolExecutor(max_workers=jobs) as ex:
        fut_map = {}
        for original_path in files:
            target_path = original_path
            is_patched = False

            if original_path.name in recheck_map:
                target_path = recheck_map[original_path.name]
                is_patched = True

            fut = ex.submit(worker, target_path)
            fut_map[fut] = (original_path, is_patched)

        low = med = high = has_key = ok_cnt = 0
        total_patched = 0

        for fut in tqdm(as_completed(fut_map), total=total, desc="统计中"):
            original_path, is_patched = fut_map[fut]
            raw_folder_name = original_path.parent.name
            category_name = extract_category(raw_folder_name)

            try:
                l, m, h, hk, ok = fut.result()
            except Exception:
                continue

            cat = category_stats[category_name]
            cat['total'] += 1
            cat['low'] += l
            cat['medium'] += m
            cat['high'] += h
            if is_patched:
                cat['patched'] += 1
                total_patched += 1

            low += l;
            med += m;
            high += h;
            has_key += hk;
            ok_cnt += ok

    def pct(num, den):
        return (num / den * 100) if den else 0.0

    # === 修改后的表格打印部分 ===
    print("\n" + "=" * 115)
    # Valid = Low + Medium + High (有效识别数)
    # High+Med = Medium + High (风险数)
    print(
        f"{'Category':<20} | {'Total':<6} | {'Valid':<6} | {'Low':<6} | {'High+Med':<8} | {'Risk%':<7} | {'Patched':<15}")
    print("-" * 115)

    for cat_name in sorted(category_stats.keys()):
        s = category_stats[cat_name]

        risk_sum = s['high'] + s['medium']
        valid_sum = s['low'] + s['medium'] + s['high']  # 三者总和

        # Risk% 依然是占 Total 的比例
        risk_pct = pct(risk_sum, s['total'])

        print(
            f"{cat_name:<20} | {s['total']:<6} | {valid_sum:<6} | {s['low']:<6} | {risk_sum:<8} | {risk_pct:6.2f}% | {s['patched']:<15}")

    print("=" * 115 + "\n")

    print(f"====== 全局统计汇总 ======")
    print(f"总文件数 (Total)   : {total}")
    print(f"有效识别 (Valid)   : {low + med + high}")
    print(f"低风险 (Low)       : {low}")
    print(f"中/高风险 (High+Med): {med + high}")
    print(f"复检覆盖数         : {total_patched}")


if __name__ == "__main__":
    sys.exit(main())