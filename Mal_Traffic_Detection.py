from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, START, END
from Input import Input
from runtime_config import get_value
from agent.EngineerAgent import EngineerAgent
from agent.ObserverAgent  import ObserverAgent
from agent.AnalystAgent import AnalystAgent
from agent.AuditorAgent import AuditorAgent
from utils.call_agent import (
    get_EngineerAgent_call_agent,
    get_AuditorAgent_call_agent,
    get_ObserverAgent_call_agent,
    get_AnalystAgent_call_agent
)
from utils.printTool import pretty_print_messages
from langgraph.checkpoint.memory import MemorySaver
from utils.handoff_Tool import(
    Train_AuditorAgent_Handoff_to_EngineerAgent,
    Det_AuditorAgent_Handoff_to_AnalystAgent_Raw_Traffic_Data,
    Det_AnalystAgent_Handoff_to_ObserverAgent,
    Det_ObserverAgent_Handoff_to_AuditorAgent,
    Det_AuditorAgent_Handoff_to_ObserverAgent,
    Det_AuditorAgent_Handoff_to_AnalystAgent_Observation_Result,
    Det_AnalystAgent_Handoff_to_AuditorAgent,
    Det_AuditorAgent_Handoff_to_AnalystAgent_Audit_Result,
    Det_AnalystAgent_save_report
)
from utils.load_prompt import get_prompt
import json
from utils.LangChainUtils import clean_state
from langchain_deepseek import ChatDeepSeek


# Detection workflow
class _:
    def __init__(self, 
                 model_name, 
                 base_url,
                 api_key : None,
                 max_tokens
                 ):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        
        # self.model = ChatOpenAI(model=model_name, base_url=base_url, api_key = api_key, max_tokens=50)
        self.model = ChatDeepSeek(model=model_name, base_url=base_url, api_key = api_key, max_tokens=max_tokens)
        # build the workflow Graph
        builder = StateGraph(MessagesState)
        
        # interaction tools
        EngineerAgent_Tools = []
        AuditorAgent_Tools = [
                                Det_AuditorAgent_Handoff_to_AnalystAgent_Raw_Traffic_Data, 
                                Det_AuditorAgent_Handoff_to_ObserverAgent,
                                Det_AuditorAgent_Handoff_to_AnalystAgent_Observation_Result,
                                Det_AuditorAgent_Handoff_to_AnalystAgent_Audit_Result
                            ]
        ObserverAgent_Tools = [Det_ObserverAgent_Handoff_to_AuditorAgent]
        AnalystAgent_Tools = [
                                Det_AnalystAgent_Handoff_to_ObserverAgent,
                                Det_AnalystAgent_Handoff_to_AuditorAgent,
                                Det_AnalystAgent_save_report
                            ]
        
        self.engineerAgent = EngineerAgent.create(
                                model = self.model,
                                tools = EngineerAgent_Tools,
                                sys_prompt = get_prompt('EngineerAgent')
                                )
        self.auditorAgent = AuditorAgent.create(
                                model = self.model,
                                tools = AuditorAgent_Tools,
                                sys_prompt= get_prompt('AuditorAgent', 'Detection')
                                )
        self.analystAgent = AnalystAgent.create(
                                model = self.model,
                                tools = AnalystAgent_Tools,
                                sys_prompt = get_prompt('AnalystAgent')
                                )
        self.observerAgent = ObserverAgent.create(
                                model = self.model,
                                tools = ObserverAgent_Tools,
                                sys_prompt = get_prompt('ObserverAgent','Detection')
                                )
        builder.add_node("EngineerAgent", get_EngineerAgent_call_agent(self.engineerAgent))
        builder.add_node("AuditorAgent", get_AuditorAgent_call_agent(self.auditorAgent))
        builder.add_node("AnalystAgent", get_AnalystAgent_call_agent(self.analystAgent))
        builder.add_node("ObserverAgent", get_ObserverAgent_call_agent(self.observerAgent))
        
        builder.add_edge(START, "EngineerAgent")
        
        self.graph = builder.compile(checkpointer=MemorySaver())
        # 设置实例
        self.config = {"configurable": {"thread_id": str(get_value("detection", "thread_id"))}}
    
    def invoke(self, fileName):
        input = Input(fileName)
        # retrieve the base64 encoding of file content 
        fileData = input.get_FileData()
        max_chars = int(get_value("detection", "max_file_base64_chars"))
        fileData = fileData[:max_chars] if len(fileData) > max_chars else fileData
        # fileData = fileData[:5000] if len(fileData) > 5000  else fileData
        clean_state(self.graph, self.config, self.graph.get_state(self.config).values)
        
        user_input = json.dumps({'local_traffic_filePath' : fileName, 'part of base64 encoding of raw byte data in traffic files' : fileData,'delete_status': True})
        for event in self.graph.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config = self.config,
        ):
            pass
            # pretty_print_messages(event)
        # clean_state_(self.graph, self.config, self.graph.get_state(self.config).values)
        # print('\n\n结束，当前状态', self.graph.get_state(self.config).values)
        