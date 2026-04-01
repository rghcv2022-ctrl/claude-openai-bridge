# claude-openai-proxy

Minimal local Anthropic-compatible proxy for Claude Code on Windows, forwarding requests to the GMN OpenAI-compatible API.

## Quick start

1. Copy `config.example.json` to `config.json`.
2. Install deps:
   `py -3.9 -m pip install -r requirements.txt`
3. Run server:
   `py -3.9 -m uvicorn app:app --host 127.0.0.1 --port 43118`

This project is intended to run locally on Windows for Claude Code. It presents an Anthropic-compatible local endpoint and routes traffic to GMN's OpenAI-compatible `/v1/chat/completions` API.

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
