import json
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI


DEFAULT_CONFIG_FILE = "config.json"


@lru_cache(maxsize=1)
def _default_config_path():
    return Path(DEFAULT_CONFIG_FILE)


def _resolve_config_path():
    config_env = os.environ.get("CLAUDE_OPENAI_PROXY_CONFIG")
    if config_env:
        return Path(config_env)
    return _default_config_path()


def load_config():
    config_path = _resolve_config_path()
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_app():
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        cfg = load_config()
        return {
            "ok": True,
            "listen": f'{cfg["listen_host"]}:{cfg["listen_port"]}',
            "upstream_base_url": cfg["upstream_base_url"],
            "default_model": cfg["default_model"],
        }

    return app


app = build_app()
