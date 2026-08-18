import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_ENV = "MAL_TRAFFIC_CONFIG"

_MISSING = object()

REQUIRED_CONFIG_KEYS = (
    ("model", "base_url"),
    ("model", "model_name"),
    ("model", "api_key"),
    ("model", "max_tokens"),
    ("code", "tmp_file_path"),
    ("code", "memory_file_path"),
    ("code", "result_file"),
    ("prompt", "sys_prompt_file"),
    ("train", "data_dir"),
    ("train", "file_pattern"),
    ("train", "recursive"),
    ("train", "success_file"),
    ("train", "fail_file"),
    ("train", "chat_memory_file"),
    ("train", "temp_memory_file"),
    ("train", "summary_trigger_messages"),
    ("detection", "chat_memory_file"),
    ("detection", "knowledge_file"),
    ("detection", "thread_id"),
    ("detection", "max_file_base64_chars"),
    ("paths", "worker_script"),
    ("paths", "input_root"),
    ("paths", "output_root"),
    ("paths", "temp_report_root"),
    ("runner", "max_workers"),
    ("runner", "show_worker_output"),
)


def config_file_path() -> Path:
    config_name = os.getenv(CONFIG_ENV, "runtime_config.json")
    path = Path(config_name)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _lookup(config: dict, keys: tuple[str, ...]) -> Any:
    value: Any = config
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(".".join(keys))
        value = value[key]
    return value


@lru_cache(maxsize=1)
def load_config() -> dict:
    path = config_file_path()
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if not isinstance(config, dict):
        raise ValueError(f"Config root must be a JSON object: {path}")

    for keys in REQUIRED_CONFIG_KEYS:
        _lookup(config, keys)

    return config


def get_value(*keys: str, default: Any = _MISSING) -> Any:
    try:
        return _lookup(load_config(), keys)
    except KeyError:
        if default is not _MISSING:
            return default
        raise


def get_path(*keys: str, default: Any = _MISSING) -> str:
    value = get_value(*keys, default=default)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Config path is empty: {'.'.join(keys)}")
    path = Path(str(value))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)
