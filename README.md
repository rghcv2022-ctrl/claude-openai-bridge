# Claude OpenAI Bridge

`claude-openai-bridge` is a local Anthropic-compatible proxy for Claude Code.
It accepts Claude `/v1/messages` requests and forwards them to an OpenAI-compatible
`/chat/completions` upstream (for example GMN).

This project is focused on Windows-first operations:
- local process scripts
- startup automation
- simple JSON config
- no browser login dependency for Claude Code

## How It Works

1. Claude Code sends requests to `ANTHROPIC_BASE_URL`.
2. This bridge translates Anthropic request format to OpenAI chat format.
3. The bridge forwards to your upstream endpoint.
4. The upstream response is translated back to Anthropic format.

Supported routes:
- `POST /v1/messages`
- `POST /v1/messages/count_tokens`
- `GET /healthz`

## Quick Start

### 1) Install dependencies

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Configure upstream

```powershell
Copy-Item .\config.example.json .\config.json
```

Edit `config.json` and set:
- `upstream_base_url`
- `upstream_api_key`
- model aliases if needed

### 3) Start bridge

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-proxy.ps1
```

### 4) Verify health

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\healthcheck.ps1
```

## Claude Code / VS Code Setup

Set the following in VS Code user settings (`settings.json`) under
`claudeCode.environmentVariables`:

```json
{
  "ANTHROPIC_BASE_URL": "http://127.0.0.1:43118",
  "ANTHROPIC_API_KEY": "local-proxy",
  "ANTHROPIC_AUTH_TOKEN": "local-proxy",
  "CLAUDE_CODE_SKIP_AUTH_LOGIN": "1"
}
```

Recommended:
- `claudeCode.disableLoginPrompt: true`

## Management Scripts

- Start: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-proxy.ps1`
- Stop: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-proxy.ps1`
- Restart: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\restart-proxy.ps1`
- Health: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\healthcheck.ps1`
- Install logon task: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-task.ps1`
- Remove logon task: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall-task.ps1`
- Install Startup shortcut: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-startup-shortcut.ps1`
- Remove Startup shortcut: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall-startup-shortcut.ps1`

If Windows denies Task Scheduler permissions, use Startup shortcut mode.

## Configuration Reference

`load_config()` reads UTF-8 JSON from:
- `CLAUDE_OPENAI_PROXY_CONFIG` when set
- `config.json` in the working directory by default

UTF-8 and UTF-8 BOM are both supported.

Key fields:
- `listen_host`
- `listen_port`
- `upstream_base_url`
- `upstream_api_key`
- `upstream_chat_path`
- `default_model`
- `request_timeout_seconds`
- `request_retry_attempts`
- `request_retry_backoff_seconds`
- `log_level`
- `model_aliases`

## Troubleshooting

- Browser login popup still appears:
  - Confirm `CLAUDE_CODE_SKIP_AUTH_LOGIN=1`
  - Confirm `claudeCode.disableLoginPrompt=true`
  - Reload VS Code window
- Intermittent no response:
  - Check `.\\logs\\proxy.stdout.log`
  - Upstream `503` means provider-side saturation or temporary upstream issue
  - Retry logic is built in (`request_retry_attempts`)
- Config parse errors:
  - Validate JSON syntax in `config.json`

## Security Notes

- `config.json` contains secrets and is intentionally ignored by Git.
- Never commit real API keys.
- Use a dedicated upstream key with scoped permissions.

## Development

Run tests:

```powershell
py -3.9 -m pytest tests -v
```
