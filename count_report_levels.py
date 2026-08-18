#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, sys, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict

# 解析 JSON，8 进程
# python count_report_levels.py ./test -j 8

# 极速正则模式（不解析 JSON）s
# python count_report_levels.py ./Mal_Traffic/report/ids2019/test_dataset -b True -j 8 --regex-fast

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


# -------- 两种 worker --------
_rx_level = re.compile(rb'"threat_level"\s*:\s*"(low|medium|high)"', re.IGNORECASE)
_rx_has_key = re.compile(rb'"threat_level"\s*:', re.IGNORECASE)


def worker_regex(path: Path):
    """
    返回: (low, medium, high, has_key, ok)
    ok=0 表示读取失败；has_key=0 表示无 threat_level 键
    """
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
    # 有 key 但不是这三类
    return (0, 0, 0, 1 if _rx_has_key.search(b) else 0, 1)


def worker_json(path: Path):
    """
    返回: (low, medium, high, has_key, ok)
    """
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
    return (0, 0, 0, 1, 1)  # 有 key 但不在三类


def main():
    ap = argparse.ArgumentParser(description="统计 threat_level=low/medium/high 的数量与占比，并按子目录分类统计")
    ap.add_argument("ROOT", help="根目录（递归扫描 JSON）")
    ap.add_argument("-p", "--pattern", default="*.json", help="匹配模式，默认 *.json")
    ap.add_argument("-j", "--jobs", type=int, default=0, help="并发进程数；默认=CPU核数")
    ap.add_argument("--regex-fast", action="store_true", help="正则极速模式（不解析 JSON）")
    ap.add_argument("-b", "--bengin", type=bool, default=False,
                    help="过滤模式：True只看包含benign路径，False过滤掉包含benign路径（注意：如果想统计所有目录，请不要依赖此参数，或者修改代码逻辑）")
    args = ap.parse_args()

    root = Path(args.ROOT).resolve()
    if not root.is_dir():
        print(f"ERROR: 目录不存在：{root}", file=sys.stderr);
        return 2

    files = [p for p in root.rglob(args.pattern) if p.is_file()]

    # 保留原有的过滤逻辑
    if args.bengin:
        filtered = [p for p in files if "benign" in p.as_posix()]
    else:
        # 如果你想一次性统计所有目录（既有benign也有malicious），可以注释掉下面这行
        filtered = [p for p in files if "benign" not in p.as_posix()]
    files = filtered

    total = len(files)
    if total == 0:
        print("未找到任何符合条件的 JSON 文件。");
        return 0

    print(f"待处理文件数: {total}")

    worker = worker_regex if args.regex_fast else worker_json
    jobs = args.jobs or None

    # 全局计数器
    low = med = high = has_key = ok_cnt = 0
    err_files = []
    no_key_files = []

    # 保存特定文件路径的列表
    low_files_list = []
    medium_files_list = []
    high_files_list = []

    # === 新增：按类别（子目录）统计 ===
    # 结构: category_stats['DNS1'] = {'low':0, 'medium':0, 'high':0, 'total':0, ...}
    category_stats = defaultdict(lambda: {'low': 0, 'medium': 0, 'high': 0, 'err': 0, 'no_key': 0, 'total': 0})

    with ProcessPoolExecutor(max_workers=jobs) as ex:
        fut_map = {ex.submit(worker, p): p for p in files}
        for fut in tqdm(as_completed(fut_map), total=total, desc="统计中", unit="file"):
            path = fut_map[fut]

            # 获取类别名称 (取文件所在的直接父目录名，例如 report/DNS1/x.json -> DNS1)
            category_name = path.parent.name

            try:
                l, m, h, hk, ok = fut.result()
            except Exception:
                err_files.append(path)
                category_stats[category_name]['err'] += 1
                category_stats[category_name]['total'] += 1
                continue

            # 更新分类统计
            cat = category_stats[category_name]
            cat['total'] += 1
            cat['low'] += l
            cat['medium'] += m
            cat['high'] += h
            if ok == 0: cat['err'] += 1
            if hk == 0: cat['no_key'] += 1

            # 更新全局统计
            low += l;
            med += m;
            high += h;
            has_key += hk;
            ok_cnt += ok

            # 记录异常文件与特定风险文件
            if ok == 0:
                err_files.append(path)
            elif hk == 0:
                no_key_files.append(path)
            elif l == 1 and not args.bengin:
                low_files_list.append(path)
            elif m == 1 and args.bengin:
                medium_files_list.append(path)
            elif h == 1 and args.bengin:
                high_files_list.append(path)

    parse_err = len(err_files)

    # 辅助函数：计算百分比
    def pct(num, den):
        return (num / den * 100) if den else 0.0

    # ==========================
    # 1. 打印分类统计表格
    # ==========================
    print("\n" + "=" * 80)
    print(f"{'Category (Folder)':<25} | {'Total':<6} | {'Low':<6} | {'Med':<6} | {'High':<6} | {'High+Med %':<10}")
    print("-" * 80)

    # 按目录名排序输出
    for cat_name in sorted(category_stats.keys()):
        s = category_stats[cat_name]
        total_files = s['total']
        # 计算高危+中危占比（用于快速判断检测率或误报率）
        risk_pct = pct(s['high'] + s['medium'], total_files)

        print(
            f"{cat_name:<25} | {total_files:<6} | {s['low']:<6} | {s['medium']:<6} | {s['high']:<6} | {risk_pct:6.2f}%")
    print("=" * 80 + "\n")

    # ==========================
    # 2. 原有的文件保存逻辑
    # ==========================
    if low_files_list:
        txt_filename = "low_risk_files.txt"
        print(f"检测到 {len(low_files_list)} 个低威胁文件(Low)，已保存至 {txt_filename}")
        with open(txt_filename, "w", encoding="utf-8") as f:
            for p in sorted(low_files_list):
                f.write(str(p) + "\n")

    risky_files = high_files_list + medium_files_list
    if risky_files:
        txt_filename = "risk_files.txt"
        print(f"检测到 {len(risky_files)} 个中/高威胁文件(Med+High)，已保存至 {txt_filename}")
        with open(txt_filename, "w", encoding="utf-8") as f:
            for p in sorted(risky_files):
                f.write(str(p) + "\n")

    # ==========================
    # 3. 全局统计汇总
    # ==========================
    recog = low + med + high
    print("\n====== 全局统计汇总 ======")
    print(f"总文件数           : {total}")
    print(f"解析成功           : {ok_cnt}  | 失败/无Key: {total - recog}")
    print(f"low / medium / high: {low} / {med} / {high}")

    print("\n—— 识别分布 (占有效识别文件) ——")
    if recog:
        print(f"low   : {pct(low, recog):6.2f}%")
        print(f"medium: {pct(med, recog):6.2f}%")
        print(f"high  : {pct(high, recog):6.2f}%")
    else:
        print("无有效识别结果。")

    return 0


if __name__ == "__main__":
    sys.exit(main())