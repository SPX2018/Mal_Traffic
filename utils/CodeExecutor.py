import subprocess
import uuid
import os
from langchain_core.tools import tool
from langgraph.types import Command
from typing import Dict
from utils.LangChainUtils import debug
import json
import yaml
from utils.LangChainUtils import debug, extract_traffic_data
from runtime_config import get_path

# execute the generated python code
def execute(codefile, filename) -> Dict:
    result = subprocess.run(
        ["python", codefile, filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10
    )
    return str({"stdout" : result.stdout.decode(), "stderr" : result.stderr.decode()}).replace("'", '"')

# 代码执行完成后，直接带结果转移到AuditorAgent
@tool('CodeExecutor')
def CodeExeWorkFlow(code : str,
                    filepath : str,
                    delete_status: bool
                    ):
    """
    execute the python program and transfer to AuditorAgent
    code : source code
    filepath : local_traffic_filePath
    delete_status: the operation mode
    """
    debug( 'EngineerAgent' , '工具调用 ==> ' + filepath)

    config = None
    codefile = get_path("code", "tmp_file_path")
    memory_codefile = get_path("code", "memory_file_path")
    result_file = get_path("code", "result_file")
    if os.path.exists(codefile):
        os.remove(codefile)

    if os.path.exists(memory_codefile):
        result = execute(memory_codefile, filepath)

        # # 保存流量提取结果到文件
        # with open('result', 'w') as f:
        #     f.write(result)

        data = extract_traffic_data(result)


        if delete_status is True:
            json_data = {
                "role": "EngineerAgent",
                "file_name": filepath,
                "type": "raw_traffic_data",
                "traffic_data": data
            }
            # print(json_data,'====json_data===',type(json_data))
            json_data = json.dumps(json_data, ensure_ascii=False, separators=(",", ":"), default=str)
            # print(json_data,'====json_data.dumps===',type(json_data))

            debug('EngineerAgent', '准备从EngineerAgent转移到AnalystAgent')
            return Command(
                goto='AnalystAgent',
                graph=Command.PARENT,
                update={"messages": [{'role': 'user', 'content': json_data}]},
            )
        else:
            data = f'{{traffic_data: {data} }}'

            content = {
                'role': 'EngineerAgent',
                "file_name": filepath,
                "related data": {"content": data}
            }
            content = json.dumps(content, ensure_ascii=False, separators=(",", ":"), default=str)
            debug('EngineerAgent', '准备从EngineerAgent转移到ObserverAgent')
            return Command(
                goto='ObserverAgent',
                graph=Command.PARENT,
                update={"messages": [{'role': 'user', 'content': content}]},
            )
    else:

        os.makedirs(os.path.dirname(codefile), exist_ok=True)
        with open(codefile, 'w') as f:
            f.write(code)
        debug('EngineerAgent', ' temp代码文件已生成' )
        result = execute(codefile, filepath)
        
        # 保存流量提取结果到文件
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(result)
        debug('EngineerAgent', ' result已写入文件')
        content = {
            'role' : 'EngineerAgent',
            "file_name": filepath,
            "related data" : {"code" : code,"code_file":codefile, "result" : result}
        }


        debug( 'EngineerAgent' ,'准备从EngineerAgent转移到AuditorAgent')
        # clean escape characters
        raw_str = json.dumps(content, ensure_ascii=False, indent=0)
        import re
        valid_escapes = "nrtbf\\'\""
        content = re.sub(r'(\\)+([' + valid_escapes + '])', lambda m: '\\' + m.group(2), raw_str)

        return Command(
                goto='AuditorAgent',
                graph=Command.PARENT,
                update={"messages": [{'role' : 'user','content' : content}]},
            )
