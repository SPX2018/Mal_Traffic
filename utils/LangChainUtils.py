from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
import json
import os
from langchain_core.messages import RemoveMessage

# Convert loaded messages into standard LangChain message objects
def to_lc_message(msg):
    if isinstance(msg, BaseMessage):
        return msg  # Already a LangChain message
    role = msg["role"]
    content = msg["content"]
    if role == "system":
        return SystemMessage(content=content)
    elif role == "user":
        return HumanMessage(content=content)
    elif role == "assistant":
        return AIMessage(content=content)
    elif role == "tool":
        return AIMessage(content=content, additional_kwargs={"tool_call_id": msg.get("tool_call_id")})
    else:
        raise ValueError(f"Unknown message role: {role}")
    
def load_chat_memory(file_path):
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)  # Expecting a full JSON array of messages
        except json.JSONDecodeError as e:
            return []
        
# **保存对话历史到 JSON**
def save_chat_memory(filename, memory):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=4)

def clean_state(graph, config, state):
    if state == {}:
        return
    messags = state["messages"]
    for message in messags:
        try:
            graph.update_state(config, {"messages" : RemoveMessage(id = message.id)})
        except Exception as e:
            print(e)

# 将记忆格式进行转换
def transfer_memory(session_memory) -> HumanMessage:
    # res = {
    #     "from" : "ObserverAgent",
    #     "to" : "ObserverAgent",
    #     "type" : "normal traffic data and learned patterns",
    #     }
    res={}
    content = []
    for item in session_memory:
        if item['role'] == 'user':
            content.append({"type" : "current_normal_traffic_data", "value" : item['content']})
        elif item['role'] == 'assistant':
            content.append({"type" : "Learned patterns", "value" : item['content']})
    res["content"] = content
    return HumanMessage(content=str(res))

# 将记忆格式进行转换
def transfer_knowledge(session_memory) -> HumanMessage:
    # res = {
    #     "from" : "ObserverAgent",
    #     "to" : "ObserverAgent",
    #     "type" : "normal traffic data and learned patterns",
    #     }
    res={}
    content = []
    for item in session_memory:
        if item['role'] == 'user':
            content.append({"type" : "malicious_traffic_characteristics", "value" : item['content']})
        elif item['role'] == 'assistant':
            content.append({"type" : "Learned patterns", "value" : item['content']})
    res["content"] = content
    return HumanMessage(content=str(res))


# 从AuditorAgent开始提取属于AuditorAgent、AnalystAgent、ObserverAgent的状态信息，避免不相关的message干扰
def cut_out_message(messages, role):
    _ = []
    from_ = f'\"from\" : \"{role}\"'
    to_ = f'\"to\" : \"{role}\"'
    from__ = f'\"from\": \"{role}\"'
    to__ = f'\"to\": \"{role}\"'
    from___ = f'\"from\":\"{role}\"'
    to___ = f'\"to\":\"{role}\"'
    for message in messages:
        content = message.content
        if from_ in content or to_ in content or from__ in content or to__ in content or from___ in content or to___ in content:
            _.append(message)
    if _ == []:
        _ = messages
    return _

# debug tool
def debug(role, message):
    print('\n')
    print(' debug::' + '<' + role + '>' + ' : ' + message )
    print('\n')
    

# 从输出中提出流量数据
def extract_traffic_data(s: str) -> str:
    # 找第一个 '[' 和最后一个 ']'
    start = s.find('[')
    end = s.rfind(']')
    if start == -1 or end == -1 or end < start:
        return s  # 找不到就原样返回
    return s[start:end+1]