from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

class ObserverAgent():
    @classmethod
    def create(cls, model, tools, sys_prompt) -> CompiledGraph:
        HandOffAgents = ['AuditorAgent', 'AnalystAgent']
        # Agent交互工具

        return create_react_agent(
            model=model,
            tools=tools,
            name="ObserverAgent",
            prompt=sys_prompt,
        )