# claude-openai-proxy

Minimal independent proxy bootstrap for Claude-to-OpenAI style routing.

## Quick start

1. Copy `config.example.json` to `config.json`.
2. Install deps:
   `py -3.9 -m pip install -r requirements.txt`
3. Run server:
   `py -3.9 -m uvicorn app:app --host 127.0.0.1 --port 43118`

## Config

`load_config()` reads UTF-8 JSON from:

- `CLAUDE_OPENAI_PROXY_CONFIG` (if set)
- `config.json` (default)

Required fields:

- `listen_host`
- `listen_port`
- `upstream_base_url`
- `upstream_api_key`
- `upstream_chat_path`
- `default_model`
- `request_timeout_seconds`
- `log_level`
- `model_aliases`

## Test

`py -3.9 -m pytest tests/test_config_and_health.py -v`
