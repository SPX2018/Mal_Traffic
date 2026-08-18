import os
import shutil
from pathlib import Path

import yaml
from langchain_core.tools import tool
from langgraph.types import Command
import uuid
import json
from utils.LangChainUtils import debug, extract_traffic_data
from runtime_config import get_path


# 给出EngineerAgent建议，重新提取流量数据
@tool("transfer_to_EngineerAgent")
def Train_AuditorAgent_Handoff_to_EngineerAgent(Suggestion: str):
    """transfer to EngineerAgent for task"""
    # debug('AuditorAgent' , '准备转移到EngineerAgent, 给出的建议 ==> ' + Suggestion)
    agent_name = "EngineerAgent"

    codefile = get_path("code", "tmp_file_path")
    os.remove(codefile)

    debug('AuditorAgent', '！！！Engineer的代码没有通过审查！')
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': Suggestion}]},
    )

# 转移到ObserverAgent进行训练
@tool("transfer_to_ObserverAgent")
def Train_AuditorAgent_Handoff_to_ObserverAgent():
    """pass the traffic data to ObserverAgent for task"""
    # debug('AuditorAgent' ,'准备转移到ObserverAgent进行训练')
    agent_name = "ObserverAgent"


    tmp_codefile = get_path("code", "tmp_file_path")
    memory_codefile = get_path("code", "memory_file_path")
    if not os.path.exists(memory_codefile):

        shutil.move(tmp_codefile, memory_codefile)
        debug('AuditorAgent', '！！！Engineer的代码终于通过了！代码已转移...')
    # 本地读取流量提取结果（LLM输出传递参数方式，太长会被截断）
    # with open('result', "r", encoding="utf-8") as f:
    #     data = extract_traffic_data(f.read())
    with open(get_path("code", "result_file"), "r", encoding="utf-8") as f:
        data = extract_traffic_data(f.read())

    data = f'{{traffic_data: {data} }}'

    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': data}]},
    )

# 转移到AnalystAgent，传递原始流量数据
@tool
def Det_AuditorAgent_Handoff_to_AnalystAgent_Raw_Traffic_Data():
    """pass the raw traffic data to AnalystAgent for task"""
    # debug('AuditorAgent' , '准备转移到AnalystAgent,传递原始流量数据')
    agent_name = "AnalystAgent"
    
    # 本地读取流量提取结果（LLM输出传递参数方式，太长会被截断）
    # with open('result', "r", encoding="utf-8") as f:
    #     data = extract_traffic_data(f.read())
    with open(get_path("code", "result_file"), "r", encoding="utf-8") as f:
        data = extract_traffic_data(f.read())

    json_data = {
        "role": "AuditorAgent",
        "type": "raw_traffic_data",
        "traffic_data" : data
    }
    # print(json_data,'====json_data===',type(json_data))
    json_data=json.dumps(json_data, ensure_ascii=False)
    # print(json_data,'====json_data.dumps===',type(json_data))
    
    
    
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': json_data}]},
    )

# AnalystAgent转移到ObserverAgent，询问流量数据
@tool
def Det_AnalystAgent_Handoff_to_ObserverAgent(json_data: str):
    """pass traffic data to ObserverAgent to observe"""
    # debug('AnalystAgent' , '准备向ObserverAgent询问流量数据')
    # print("AnalystAgent准备向ObserverAgent询问流量数据--->",json_data)
    agent_name = "ObserverAgent"
    
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': json_data}]},
    )

# ObserverAgent转移到AuditorAgent，传递观察结果
@tool
def Det_ObserverAgent_Handoff_to_AuditorAgent(observation_result: str):
    """pass the Observation results to AuditorAgent"""
    # debug( 'ObserverAgent' ,'准备向AuditorAgent提交观察结果')
    
    agent_name = "AuditorAgent"
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': observation_result}]},
    )

# AuditorAgent转移到ObserverAgent，传递建议
@tool
def Det_AuditorAgent_Handoff_to_ObserverAgent(Suggestion: str):
    """Provide ObserverAgent suggestions and transfer to it"""
    # debug( 'AuditorAgent' ,'准备转移到ObserverAgent, 给出的建议 ==> ' + Suggestion)
    
    agent_name = "ObserverAgent"
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': Suggestion}]},
    )

# AuditorAgent转移到AnalystAgent，传递观察结果
@tool
def Det_AuditorAgent_Handoff_to_AnalystAgent_Observation_Result(json_data: str):
    """Pass the correct Observation results to AnalystAgent"""
    # debug( 'AuditorAgent' , '准备转移到AnalystAgent,传递观察结果')
    
    agent_name = "AnalystAgent"
    
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': json_data}]},
    )

# AnalystAgent转移到AuditorAgent，传递分析结果
@tool
def Det_AnalystAgent_Handoff_to_AuditorAgent(analysis_results: str):
    """Pass the Analysis report to AuditorAgent"""
    # debug('AnalystAgent' , '准备转移到AuditorAgent,传递分析结果')
    
    agent_name = "AuditorAgent"
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': analysis_results}]},
    )

# AuditorAgent转移到AnalystAgent，传递审计结果
@tool
def Det_AuditorAgent_Handoff_to_AnalystAgent_Audit_Result(json_data: str):
    """Pass the Audit Suggestion to AnalystAgent"""
    # debug( 'AuditorAgent' ,'准备转移到AnalystAgent,传递审计结果 ==> '+json_data)


    agent_name = "AnalystAgent"
    return Command(
        # navigate to another agent node in the PARENT graph
        goto=agent_name,
        graph=Command.PARENT,
        update={"messages": [{'role' :'user', 'content': json_data}]},
    )

def _temp_report_path(dir_name: str) -> str:
    temp_root = os.getenv(
        "REPORT_TEMP_ROOT",
        get_path("paths", "temp_report_root")
    )
    current_base = os.getenv("REPORT_CURRENT_BASENAME", "")
    if not current_base:
        current_file = os.getenv("REPORT_CURRENT_FILE", "")
        current_base = Path(current_file).stem if current_file else "unknown"
    category = dir_name or os.getenv("REPORT_CATEGORY", "unknown")
    os.makedirs(temp_root, exist_ok=True)
    file_name = os.path.join(temp_root, f"{category}__{current_base}__report_{uuid.uuid4().hex}.json")
    print("temp_report_path:" + file_name)
    return file_name

def _fallback_report_path() -> str:
    report_root = os.getenv(
        "REPORT_FALLBACK_ROOT",
        get_path("paths", "temp_report_root")
    )
    category = os.getenv("REPORT_CATEGORY", "")
    current_file = os.getenv("REPORT_CURRENT_FILE", "")
    current_base = os.getenv("REPORT_CURRENT_BASENAME", "")
    if not category and current_file:
        category = Path(current_file).parent.name
    if not current_base and current_file:
        current_base = Path(current_file).stem
    category = category or "unknown"
    current_base = current_base or "unknown"
    os.makedirs(report_root, exist_ok=True)
    file_name = os.path.join(report_root, f"{category}__{current_base}__report_{uuid.uuid4().hex}.json")
    print("fallback_report_path:" + file_name)
    return file_name

def _extract_report_file_path(data: dict) -> str:
    candidates = [
        data.get("traffic_summary", {}).get("file_name"),
        data.get("analysis_report", {}).get("traffic_summary", {}).get("file_name"),
        data.get("content", {}).get("traffic_summary", {}).get("file_name"),
        data.get("content", {}).get("analysis_report", {}).get("traffic_summary", {}).get("file_name"),
        data.get("file_name"),
        data.get("content", {}).get("file_name"),
    ]
    for file_path in candidates:
        if file_path:
            return file_path
    raise KeyError("traffic_summary.file_name")

# AnalystAgent保存报告
@tool
def Det_AnalystAgent_save_report(report: str):
    """AnalystAgent save report"""
    # debug( 'AnalystAgent' ,'准备保存报告')
    try:
        # 1. 将字符串解析为 Python 字典
        data = json.loads(report)

        file_path = _extract_report_file_path(data)

        # 3. 使用 pathlib 提取父目录名称
        dir_name = Path(file_path).parent.name
        if not dir_name:
            raise KeyError(f"empty category name from file_path: {file_path}")
        fileName = _temp_report_path(dir_name)
    except json.JSONDecodeError:
        # print("字符串格式不是有效的 JSON")
        # # 1. 使用正则直接定位 "file_name": "..." 模式
        # # 这里的正则会捕获引号内的路径
        # match = re.search(r'"file_name":\s*"([^"]+)"', report)
        #
        # if match:
        #     full_path = match.group(1)
        #     # 2. 提取上级目录
        #     dir_name = Path(full_path).parent.name
        #     fileName = 'report/temp/' + dir_name + '_temp/' + '/report_' + uuid.uuid4().hex + '.json'
        # else:
        #     print("未找到 file_name")
        #     fileName = 'report/report_' + uuid.uuid4().hex + '.json'
        fileName = _fallback_report_path()
        print("字符串格式不是有效的 JSON")
    except KeyError:
        fileName = _fallback_report_path()
        print("未找到 file_name 字段")
    with open(fileName, 'w') as f:
        f.write(report)
        print("fileName："+fileName)
    debug( 'AnalystAgent' , '保存报告成功')
