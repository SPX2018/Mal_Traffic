import yaml

from runtime_config import get_path

prompt_file = get_path("prompt", "sys_prompt_file")

with open(prompt_file, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

def get_prompt(AgentName, prompt_type = 'Detection'):
    try:
        prompt = config[AgentName]['prompt'][prompt_type]
        return prompt
    except KeyError:
        raise KeyError(f"Get Prompt Error: {AgentName} or {prompt_type} not found in sys_prompt.yml")

