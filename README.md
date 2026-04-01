# Claude OpenAI Proxy

Local Anthropic-compatible proxy for Claude Code on Windows. The proxy listens on
`127.0.0.1:43118`, accepts Claude-style `/v1/messages` requests, and forwards them
to a GMN OpenAI-compatible `chat/completions` upstream.

## Setup

1. Copy `config.example.json` to `config.json`.
2. Fill in your real GMN `upstream_base_url` and `upstream_api_key`.
3. Use the PowerShell scripts below to manage the proxy lifecycle.

## Commands

- Start: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-proxy.ps1`
- Stop: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-proxy.ps1`
- Restart: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\restart-proxy.ps1`
- Health: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\healthcheck.ps1`
- Install logon task: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-task.ps1`
- Remove logon task: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall-task.ps1`

If Windows returns `Access is denied` while installing the logon task, run that command in a session that has permission to create Task Scheduler entries for your account.

## Config

`load_config()` reads UTF-8 JSON from:

- `CLAUDE_OPENAI_PROXY_CONFIG` when set
- `config.json` in the working directory by default

Both plain UTF-8 JSON and UTF-8 with BOM are supported.

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

`py -3.9 -m pytest tests -v`
