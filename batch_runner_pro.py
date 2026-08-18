import os
import sys
import time
import subprocess
from multiprocessing import Pool
from runtime_config import config_file_path, get_path, get_value

# 引入进度条库，如果没安装会报错，建议 pip install tqdm
try:
    from tqdm import tqdm
except ImportError:
    print("建议安装进度条库: pip install tqdm")


    # 如果没安装，做一个假的 tqdm，防止代码报错
    def tqdm(iterable, total=None):
        return iterable

# ================= 配置区域 =================
WORKER_SCRIPT = get_path("paths", "worker_script")
# INPUT_ROOT = "./dataset/USTC-TFC2016/test_simple_mask_payload"
INPUT_ROOT = get_path("paths", "input_root")
OUTPUT_ROOT = get_path("paths", "output_root")

# 你的CPU有24核，建议设置 6-10 个并发
# 这样既能跑得快，又不会把 API 或者是磁盘 IO 堵死
MAX_WORKERS = int(get_value("runner", "max_workers", default=1))
SHOW_WORKER_OUTPUT = bool(get_value("runner", "show_worker_output", default=True))


# ===========================================

def run_task(args):
    """
    子进程执行的函数
    """
    subdir_name, input_path, output_path = args

    # 构造命令
    cmd = [sys.executable, WORKER_SCRIPT, input_path, output_path]

    try:
        # capture_output=True 会把子脚本的 print 内容捕获，不显示在屏幕上
        # 这样屏幕上只有整洁的进度条。如果你想看报错，可以在异常里打印 result.stderr
        print("运行 " + " ".join(cmd), flush=True)
        if SHOW_WORKER_OUTPUT:
            result = subprocess.run(cmd, check=True)
            return (subdir_name, True, "")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return (subdir_name, True, result.stdout)
    except subprocess.CalledProcessError as e:
        # 如果报错了，把错误信息返回
        msg = ""
        if e.stdout:
            msg += e.stdout
        if e.stderr:
            msg += "\n[stderr]\n" + e.stderr
        if not msg:
            msg = f"returncode={e.returncode}"
        return (subdir_name, False, msg)
    except Exception as e:
        return (subdir_name, False, str(e))


if __name__ == "__main__":
    print(f"config file: {config_file_path()}")
    print(f"input root: {INPUT_ROOT}")
    print(f"output root: {OUTPUT_ROOT}")
    print(f"max workers: {MAX_WORKERS}")

    # 1. 路径检查
    if not os.path.exists(WORKER_SCRIPT):
        print(f"错误: 找不到脚本 {WORKER_SCRIPT}")
        sys.exit(1)
    if not os.path.exists(INPUT_ROOT):
        print(f"错误: 找不到输入目录 {INPUT_ROOT}")
        sys.exit(1)

    # 2. 生成任务列表
    tasks = []
    entries = os.listdir(INPUT_ROOT)
    for entry in entries:
        input_full_path = os.path.join(INPUT_ROOT, entry)
        if os.path.isdir(input_full_path):
            output_full_path = os.path.join(OUTPUT_ROOT, entry)
            # 自动创建输出子目录
            if not os.path.exists(output_full_path):
                os.makedirs(output_full_path)
            tasks.append((entry, input_full_path, output_full_path))

    total_tasks = len(tasks)
    print(f"发现 {total_tasks} 个文件夹任务。")
    print(f"启动 {MAX_WORKERS} 个并行进程...")
    print("=" * 60)

    # 3. 启动进程池 (核心逻辑)
    # imap_unordered 的特点是：谁先跑完，就先返回谁的结果
    # 配合 tqdm，可以实现流畅的进度条
    results = []
    with Pool(processes=MAX_WORKERS) as pool:
        # 使用 tqdm 显示进度条
        with tqdm(total=total_tasks, unit="task") as pbar:
            for subdir, success, msg in pool.imap_unordered(run_task, tasks):

                # 这里是只要有一个任务完成，就会执行一次
                if success:
                    pbar.set_description(f"完成: {subdir}")
                else:
                    pbar.set_description(f"失败: {subdir}")
                    # 如果失败，把错误日志打印出来，防止被进度条吞掉
                    tqdm.write(f"\n[ERROR] {subdir} 处理失败:\n{msg}\n")

                pbar.update(1)  # 进度条 +1
                results.append(success)

    # 4. 总结
    success_count = sum(results)
    fail_count = total_tasks - success_count

    print("=" * 60)
    print(f"全部完成！成功: {success_count}, 失败: {fail_count}")
