from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

class AuditorAgent():
    @classmethod
    def create(cls, model, tools, sys_prompt) -> CompiledGraph:
        # HandOffAgents = ['EngineerAgent', 'ObserverAgent', 'AnalystAgent']
        HandOffAgents = ['EngineerAgent']

        return create_react_agent(
            model=model,
            tools=tools,
            name="AuditorAgent",
            prompt=sys_prompt,
        )