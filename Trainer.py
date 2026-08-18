# 训练workflow
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, START
from Input import Input
from runtime_config import get_value
from agent.EngineerAgent import EngineerAgent
from agent.ObserverAgent  import ObserverAgent
from agent.AuditorAgent import AuditorAgent
from utils.call_agent import get_Train_call_agent
from langgraph.checkpoint.memory import MemorySaver
from utils.load_prompt import get_prompt
from utils.LangChainUtils import clean_state
import json
from utils.handoff_Tool import(
    Train_AuditorAgent_Handoff_to_EngineerAgent,
    Train_AuditorAgent_Handoff_to_ObserverAgent
)
from utils.printTool import pretty_print_messages
from langchain_core.runnables import RunnableConfig

# Train workflow
class Trainer:
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
        
        self.model = ChatOpenAI(model=model_name, base_url=base_url, api_key = api_key, max_tokens = max_tokens)
        
        # build the workflow Graph
        builder = StateGraph(MessagesState)
        # interaction tools
        EngineerAgent_Tools = []
        AuditorAgent_Tools = [Train_AuditorAgent_Handoff_to_EngineerAgent, Train_AuditorAgent_Handoff_to_ObserverAgent]
        ObserverAgent_Tools = []
        
        self.engineerAgent = EngineerAgent.create(
                                model = self.model, 
                                tools = EngineerAgent_Tools, 
                                sys_prompt = get_prompt('EngineerAgent')
                                )
        self.auditorAgent = AuditorAgent.create(
                                model = self.model, 
                                tools = AuditorAgent_Tools,
                                sys_prompt = get_prompt('AuditorAgent','Train')
                                )
        self.observerAgent = ObserverAgent.create(
                                model = self.model, 
                                tools = ObserverAgent_Tools,
                                sys_prompt = get_prompt('ObserverAgent','Train')
                                )
        builder.add_node("EngineerAgent", get_Train_call_agent(self.engineerAgent))
        builder.add_node("AuditorAgent", get_Train_call_agent(self.auditorAgent))
        builder.add_node("ObserverAgent", get_Train_call_agent(self.observerAgent))
        builder.add_edge(START, "EngineerAgent")
        
        self.graph = builder.compile(checkpointer=MemorySaver())
    
    def invoke(self, fileName):
        print(fileName)
        input = Input(fileName)
        # clean state
        config = RunnableConfig(
            configurable={"thread_id": str(get_value("detection", "thread_id"))},
            recursion_limit=35,
        )
        clean_state(self.graph, config, self.graph.get_state(config).values)
        
        # retrieve the base64 encoding of file content 
        fileData = input.get_FileData()
        max_chars = int(get_value("detection", "max_file_base64_chars"))
        fileData = fileData[:max_chars] if len(fileData) > max_chars else fileData
        # fileData = fileData[:5000] if len(fileData) > 5000  else fileData
        user_input = json.dumps({'local_traffic_filePath' : fileName, 'part of base64 encoding of raw byte data in traffic files' : fileData,'delete_status': False})
     
        for event in self.graph.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config = config,
        ):
            pass
            # pretty_print_messages(event)
        print('训练结束......')
        