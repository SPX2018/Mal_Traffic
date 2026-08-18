import langchain_core.messages
from langgraph.graph import MessagesState
from utils.load_prompt import get_prompt
from utils.LangChainUtils import load_chat_memory, to_lc_message, save_chat_memory, cut_out_message, transfer_memory, transfer_knowledge
from langgraph.graph import END
from langgraph.types import Command
import json
from runtime_config import get_path, get_value
# ***** Train workflow call agent *****
def get_Train_call_agent(agent):
    
    def call_agent(
        state: MessagesState,
    ):
        if agent.name == 'ObserverAgent':
            # 直接将流量数据传递给ObserverAgent
            print('ObserverAgent，当前状态 ==>'+ state["messages"][-1].content)
            state["messages"] = state["messages"][-1:]
            # filename = "memory/chat_memory_USTC-TFC2016.json"
            filename = get_path("train", "chat_memory_file")
            # temp = "memory/temp_USTC-TFC2016.json"
            temp = get_path("train", "temp_memory_file")
            temp_session_memory = load_chat_memory(temp)
            temp_session_memory.append({"role": "user", "content": state["messages"][-1].content})
            messages ={"messages" : [to_lc_message(m) for m in temp_session_memory] }
            ai_msg = agent.invoke(messages)
            ai_msg_content = ai_msg["messages"][-1].content
            ai_msg_content = ' '.join(ai_msg_content.split())
            temp_session_memory.append({"role": "assistant", "content": ai_msg_content})

            prompt = "将你之前学习到的正常流量的模式，重新总结合并成一个json格式的输出。对于payload字段，对以往传输的payload进行总结概括。"
            # if len(temp_session_memory) >= 20: # 因为每一个pcap要append user和 assustant，所以20才是10个pcap
            if len(temp_session_memory) >= int(get_value("train", "summary_trigger_messages")):
                session_memory = load_chat_memory(filename)
                temp_session_memory.append({"role": "user", "content":prompt})
                messages ={"messages" : [to_lc_message(m) for m in temp_session_memory] }
                ai_msg = agent.invoke(messages)
                ai_msg_content = ai_msg["messages"][-1].content
                ai_msg_content = ' '.join(ai_msg_content.split())
                temp_session_memory = []
                session_memory.append({"role": "user", "content":prompt})
                session_memory.append({"role": "assistant", "content": ai_msg_content})
                save_chat_memory(filename, session_memory)
                print("ObserverAgent学习了正常流量的模式")
            # save the memory
            save_chat_memory(temp, temp_session_memory)
            print("-------------------------------------保存成功")
            
            # End of current train workflow

            return Command(
                goto=END,
                update={"messages": [{"role" : "ai", "content" : "ending"}]}
            )
        
        # print('debug::到达新的agent ==>', agent.name, '截取之后携带的消息 ==>', state["messages"])
        if agent.name == 'EngineerAgent':
            print('到达EngineerAgent，当前状态 ==>'+ state["messages"][-1].content)
        
        if agent.name == 'AuditorAgent':
            print('到达AuditorAgent，当前状态 ==>'+ state["messages"][-1].content)
            # state["messages"] = state["messages"][-1:]
            # print(f"AuditorAgent state[messages] ->{state['messages']}")
        result = agent.invoke(state)
        return result
    
    return call_agent


# ***** Detection workflow call agent *****

# custom interact with other agents
def get_EngineerAgent_call_agent(agent):
    # call_EngineerAgent function
    def call_agent(
        state: MessagesState,
    ):
        return agent.invoke(state)
    
    return call_agent
    
def get_AuditorAgent_call_agent(agent):
    # call_AuditorAgent function
    def call_agent(
        state: MessagesState,
    ):
        
        # 如果AnalystAgent的报告中没有from和to字段，手动添加
        # content = json.loads(state["messages"][-1].content)
        content = state["messages"][-1].content
        try:
            if "analysis_report" in content or "traffic_summary" in content:
                content = json.loads(content)
                if not all(key in content for key in ["from", "to"]):
                    res = {"from" : "AnalystAgent","to" : "AuditorAgent","type": "analysis_report"}
                    if "analysis_report" in content:   
                        res.update(content)
                    if "traffic_summary" in content:
                        res["analysis_report"] = content
                    state["messages"][-1].content = json.dumps(res)
            else:
                content = json.loads(content)
                if "AnalystAgent" in list(content.values()):
                    if not all(key in content for key in ["from", "to"]):
                        res = {"from": "AnalystAgent", "to": "AuditorAgent"}
                        res["content"] = content
                        state["messages"][-1].content = json.dumps(res)
                elif "ObserverAgent" in list(content.values()):
                    if not all(key in content for key in ["from", "to"]):
                        res = {"from": "ObserverAgent", "to": "AuditorAgent"}
                        res["content"] = content
                        state["messages"][-1].content = json.dumps(res)
        except json.JSONDecodeError:
            print("Warning: content is not valid JSON")

        # 截取消息
        state["messages"] = cut_out_message(state["messages"], "AuditorAgent")
        # print("state['messages'][-1].content ",state["messages"][-1].content )
        print('数据到达审计者，截取后的消息 ==>', state["messages"][-1].content)
        return agent.invoke(state)

    return call_agent

session_memory = None

def get_ObserverAgent_call_agent(agent):
    # call_ObserverAgent function
    def call_agent(
        state: MessagesState,
    ):
        # 加载训练记忆
        global session_memory
        filename = get_path("detection", "chat_memory_file")
        if session_memory is None:
            session_memory = load_chat_memory(filename)
            session_memory = [item for item in session_memory if item.get("role") != "user"]
            session_memory = transfer_memory(session_memory)
        # 截取消息
        content = state["messages"][-1].content
        try:
            content = json.loads(content)
            if "EngineerAgent" in list(content.values()):
                if not all(key in content for key in ["from", "to"]):
                    res = {"from": "EngnieerAgent", "to": "ObserverAgent"}
                    res["content"] = content
                    state["messages"][-1].content = json.dumps(res)
            elif "AnalystAgent" in list(content.values()):
                if not all(key in content for key in ["from", "to"]):
                    res = {"from": "AnalystAgent", "to": "ObserverAgent"}
                    res["content"] = content
                    state["messages"][-1].content = json.dumps(res)
            elif "AuditorAgent" in list(content.values()):
                if not all(key in content for key in ["from", "to"]):
                    res = {"from": "AuditorAgent", "to": "ObserverAgent"}
                    res["content"] = content
                    state["messages"][-1].content = json.dumps(res)
        except json.JSONDecodeError:
            print("Warning: content is not valid JSON")

        state["messages"] = cut_out_message(state["messages"], "ObserverAgent")

        # 将记忆传递给ObserverAgent
        state["messages"].insert(0, session_memory)

         # 传入判断依据
        knowledge = load_chat_memory(get_path("detection", "knowledge_file"))
        knowledge = transfer_knowledge(knowledge)
        state["messages"].insert(0, knowledge)
        
        print('数据到达观察者，截取后的消息 ==>', state["messages"][-1].content)
        # 调用ObserverAgent
        return agent.invoke(state)

    return call_agent

def get_AnalystAgent_call_agent(agent):
    # call_AnalystAgent function
    def call_agent(
        state: MessagesState,
    ):
        to_Det_AnalystAgent_Handoff_to_AuditorAgent_flag = False
        content = state["messages"][-1].content
        try:
            content = json.loads(content)
            if "EngineerAgent" in list(content.values()):
                if not all(key in content for key in ["from", "to"]):
                    res = {"from": "EngnieerAgent", "to": "AnalystAgent"}
                    res["content"] = content
                    state["messages"][-1].content = json.dumps(res)
            elif "ObserverAgent" in list(content.values()):
                if not all(key in content for key in ["from", "to"]):
                    res = {"from": "AuditorAgent", "to": "AnalystAgent","type": "ObserverAgent_result"}
                    res["content"] = content
                    state["messages"][-1].content = json.dumps(res)
                    to_Det_AnalystAgent_Handoff_to_AuditorAgent_flag = True
            elif "AuditorAgent" in list(content.values()):
                if not all(key in content for key in ["from", "to"]):
                    res = {"from": "AuditorAgent", "to": "AnalystAgent"}
                    res["content"] = content
                    state["messages"][-1].content = json.dumps(res)
        except json.JSONDecodeError:
            print("Warning: content is not valid JSON")

        # 截取消息
        state["messages"] = cut_out_message(state["messages"], "AnalystAgent")
        print('数据到达分析者，截取后的消息 ==>', state["messages"][-1].content)
        # print('数据到达分析者')
        # print("audit_result->",state["messages"][-1].content["audit_result"])
        # if to_Det_AnalystAgent_Handoff_to_AuditorAgent_flag:
        #     return agent.invoke(state, tool_choice={"type": "tool", "name": "Det_AnalystAgent_Handoff_to_AuditorAgent"})
        # try:
        #     if "audit_result" in state["messages"][-1].content:
        #         if "The analysis result is correct" in state["messages"][-1].content["audit_result"] :
        #             print("AuditorAgent通过了审核，尝试直接调用报告保存工具！")
        #             return agent.invoke(state,tool_choice = {"type": "tool", "name": "Det_AnalystAgent_save_report"})
        # except Exception:
        #     print("尝试直接调用报告保存工具失败")
        # print('数据到达分析者，截取后的消息 ==>', state["messages"][-1].content)
        return agent.invoke(state)
    
    return call_agent