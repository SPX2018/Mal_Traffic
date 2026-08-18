from Trainer import Trainer
from runtime_config import get_path, get_value
from Mal_Traffic_Detection import _
from langchain_core.messages import AIMessage
import os
from tqdm import tqdm
import pickle



instance = Trainer(
    model_name=get_value("model", "model_name"),
    base_url=get_value("model", "base_url"),
    api_key=get_value("model", "api_key"),
    max_tokens=int(get_value("model", "max_tokens")),
)

# folder_path = './dataset/USTC-TFC2016/train_simple/'
folder_path = get_path("train", "data_dir")

# 获取所有文件
all_files = [f for f in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, f))]

# 已经完成训练的文件
# success_path = "./memory/success_USTC-TFC2016.txt"
success_path = get_path("train", "success_file")

success = []
if not os.path.exists(success_path):
    with open(success_path, 'w', encoding='utf-8') as f:
        print("文件不存在，创建文件。")
else:
    with open(success_path, 'r', encoding='utf-8') as f:
        success = [line.strip() for line in f.readlines()]

# 失败的文件
# fail_path = "./memory/fail_USTC-TFC2016.txt"
fail_path = get_path("train", "fail_file")
fail = []

# 带进度条处理文件
for file_name in tqdm(all_files, desc="处理文件中"):
    # 跳过已处理文件
    if file_name in success:
        continue

    # 执行分析操作
    file_path = os.path.join(folder_path, file_name)
    events = instance.invoke(file_path)
    success.append(file_name)
    # 实时更新成功文件（防止程序中断丢失进度）
    with open(success_path, 'a', encoding='utf-8') as f:
        f.write(f"{file_name}\n")
    

print(f"处理完成！成功{len(success)}个，失败: {len(fail)}个")

# 保存失败列表
with open(fail_path, "w", encoding="utf-8") as f:
    f.write("\n".join(fail))

# 保存成功列表
with open(success_path, "w", encoding="utf-8") as f:
    f.write("\n".join(success))
