from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

class AnalystAgent():
    @classmethod
    def create(cls, model, tools, sys_prompt) -> CompiledGraph:
        HandOffAgents = ['AuditorAgent', 'ObserverAgent']

        # 附加分析工具
        # analyze_tools = []
        # tools.extend(analyze_tools)

        return create_react_agent(
            model=model,
            tools=tools,
            name="AnalystAgent",
            prompt=sys_prompt,
        )