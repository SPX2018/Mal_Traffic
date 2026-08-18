from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from utils.CodeExecutor import CodeExeWorkFlow

class EngineerAgent():
    @classmethod
    def create(cls, model, tools, sys_prompt) -> CompiledGraph:
        HandOffAgents = ['AuditorAgent']
        # add the codeExe tool
        tools.append(CodeExeWorkFlow)
        return create_react_agent(
            model=model,
            tools=tools,
            name="EngineerAgent",
            prompt=sys_prompt,
        )