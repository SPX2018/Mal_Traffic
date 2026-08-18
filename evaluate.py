import os
import json

dir_path = "./report/benign"

def get_files_in_directory(directory):
    """返回目录中所有文件的路径列表（不包括子目录）"""
    return [os.path.join(directory, f) for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))]

files = get_files_in_directory(dir_path)
report_true = 0
fault = []

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
            # 使用安全的字典访问方式
            result = report.get("analysis_report", {}).get("traffic_classification")
          
            if result.replace(" ", "") == "normal":  # 注意这里需要冒号
                report_true += 1
            else:  # 这里也需要冒号
                fault.append(os.path.basename(file_path))
                
    except json.JSONDecodeError:
        print(f"文件 {file_path} 不是有效的JSON格式")
        fault.append(os.path.basename(file_path))
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {str(e)}")
        fault.append(os.path.basename(file_path))

# 只在最后打印一次结果
print(f"恶意报告数量: {report_true}")
print(f"非恶意或错误文件: {fault}")
