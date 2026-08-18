from Trainer import Trainer
from Mal_Traffic_Detection import _
from langchain_core.messages import AIMessage
import os
from tqdm import tqdm
import pickle
from runtime_config import get_path, get_value

deep_key = get_value("model", "api_key")
model_name = get_value("model", "model_name")
base_url = get_value("model", "base_url")


instance = _(
    model_name = model_name,
    base_url = base_url,
    api_key = deep_key,
    max_tokens = int(get_value("model", "max_tokens"))
)
def detect(input_dir,output_dir):

    folder_path = input_dir
    temp_root = os.path.abspath(get_path("paths", "temp_report_root"))
    report_category = os.path.basename(output_dir)
    os.environ["REPORT_TEMP_ROOT"] = temp_root
    os.environ["REPORT_FALLBACK_ROOT"] = temp_root
    os.environ["REPORT_CATEGORY"] = report_category
    old_report_dir = temp_root
    new_report_dir = output_dir
    os.makedirs(old_report_dir, exist_ok=True)
    os.makedirs(new_report_dir, exist_ok=True)
    # 获取所有文件
    all_files = [f for f in os.listdir(folder_path)
                 if os.path.isfile(os.path.join(folder_path, f))]

    # 未成功生成报告的文件
    fail = []

    # 原有的报告
    report = set(os.listdir(new_report_dir))

    # 带进度条处理文件
    for file_name in tqdm(all_files, desc="处理文件中"):
        base_name = os.path.splitext(file_name)[0]  # 去除扩展名
        # 跳过已处理文件
        if base_name + '.json' in report:
            continue

        file_path = os.path.join(folder_path, file_name)
        os.environ["REPORT_CURRENT_FILE"] = file_path
        os.environ["REPORT_CURRENT_BASENAME"] = base_name
        report_prefix = f"{report_category}__{base_name}__"

        # 获取处理前的报告文件列表
        before_reports = {
            name for name in os.listdir(old_report_dir)
            if name.startswith(report_prefix) and name.endswith(".json")
        }

        # 执行分析操作
        events = instance.invoke(file_path)

        print(f"{file_path}检测结束！")
        # 获取处理后的报告文件列表
        after_reports = {
            name for name in os.listdir(old_report_dir)
            if name.startswith(report_prefix) and name.endswith(".json")
        }

        # 查找新增报告
        new_report = after_reports - before_reports

        if new_report:
            report_file = new_report.pop()  # 从集合中取出一个文件名
            old_path = os.path.join(old_report_dir, report_file)
            new_path = os.path.join(new_report_dir, base_name + ".json")

            os.rename(old_path, new_path)

            report.add(base_name + ".json")
        else:
            fail.append(file_path)

    print(f"处理完成！成功生成报告: {len(report)-1}个，失败: {len(fail)}个") #扣掉已经在文件夹中的fail.txt

    # 保存失败列表
    with open(os.path.join(new_report_dir, "fail.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(fail))
