import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def make_config(**overrides):
    config = {
        "listen_host": "127.0.0.1",
        "listen_port": 43118,
        "upstream_base_url": "https://gmncode.cn/v1",
        "upstream_api_key": "test-key",
        "upstream_chat_path": "/chat/completions",
        "default_model": "gpt-5.4",
        "request_timeout_seconds": 600,
        "log_level": "INFO",
        "model_aliases": {
            "claude-*": "gpt-5.4",
            "claude-sonnet*": "gpt-5.4",
            "claude-opus*": "gpt-5.4",
            "claude-haiku*": "gpt-5.4",
            "sonnet": "gpt-5.4",
            "opus": "gpt-5.4",
            "haiku": "gpt-5.4",
        },
    }
    config.update(overrides)
    return config


def write_config(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
