from Trainer import Trainer
from Mal_Traffic_Detection import _
from langchain_core.messages import AIMessage
import os
from tqdm import tqdm
import pickle

deep_key = '-'

model_name=""

base_url = ""

# instance = Trainer(
#     model_name = model_name,
#     base_url = base_url,
#     api_key = deep_key,
#     max_tokens = 8000
# )

instance = _(
    model_name = model_name,
    base_url = base_url,
    api_key = deep_key,
    max_tokens = 8000
)

fileName = './dataset/USTC-TFC2016-test_dataset/Cridex/group_003.pcap'

for i in range(1):

    events = instance.invoke(fileName)
    




# folder_path = 'train_dataset/Monday_200'
# checkpoint_file = 'progress.pkl'  # 新增：检查点文件

# # 新增：加载已处理的文件集合
# if os.path.exists(checkpoint_file):
#     with open(checkpoint_file, 'rb') as f:
#         processed_files = pickle.load(f)
# else:
#     processed_files = set()

# # 获取所有文件（排除已处理文件）
# all_files = [f for f in os.listdir(folder_path) 
#              if (os.path.isfile(os.path.join(folder_path, f)) and 
#                  f not in processed_files)]  # 新增：过滤已处理文件

# # 带进度条处理文件
# for file_name in tqdm(all_files, desc="处理文件中"):
#     file_path = os.path.join(folder_path, file_name)
    

#     events = instance.invoke(file_path)
        
#     # 记录成功处理的文件
#     processed_files.add(file_name)
#     with open(checkpoint_file, 'wb') as f:
#         pickle.dump(processed_files, f)


# # 新增：完成后清理检查点
# if os.path.exists(checkpoint_file):
#     os.remove(checkpoint_file)
# print("所有文件处理完成！")