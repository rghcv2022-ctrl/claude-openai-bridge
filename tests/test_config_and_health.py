import json

from fastapi.testclient import TestClient

from app import build_app, load_config
from bridge import resolve_upstream_model
from conftest import make_config, write_config


def test_load_config_reads_json_from_env(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    write_config(config_path, make_config(model_aliases={"claude-sonnet-4-5": "gpt-5.4"}))
    monkeypatch.setenv("CLAUDE_OPENAI_PROXY_CONFIG", str(config_path))

    cfg = load_config()
    assert set(cfg.keys()) == {
        "listen_host",
        "listen_port",
        "upstream_base_url",
        "upstream_api_key",
        "upstream_chat_path",
        "default_model",
        "request_timeout_seconds",
        "log_level",
        "model_aliases",
    }


def test_load_config_reads_default_config_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    write_config(config_path, make_config(upstream_api_key="k", model_aliases={}))
    monkeypatch.delenv("CLAUDE_OPENAI_PROXY_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)

    cfg = load_config()
    assert cfg["listen_host"] == "127.0.0.1"
    assert cfg["listen_port"] == 43118


def test_load_config_reads_utf8_bom_json_from_env(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(make_config(model_aliases={"claude-sonnet-4-5": "gpt-5.4"})),
        encoding="utf-8-sig",
    )
    monkeypatch.setenv("CLAUDE_OPENAI_PROXY_CONFIG", str(config_path))

    cfg = load_config()
    assert cfg["default_model"] == "gpt-5.4"


def test_healthz_reads_json_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    write_config(config_path, make_config(model_aliases={"claude-sonnet-4-5": "gpt-5.4"}))
    monkeypatch.setenv("CLAUDE_OPENAI_PROXY_CONFIG", str(config_path))

    client = TestClient(build_app())
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "listen": "127.0.0.1:43118",
        "upstream_base_url": "https://gmncode.cn/v1",
        "default_model": "gpt-5.4",
    }


def test_resolve_upstream_model_uses_exact_alias():
    aliases = {"sonnet": "gpt-5.4"}
    resolved = resolve_upstream_model("sonnet", "gpt-5.4-mini", aliases)
    assert resolved == "gpt-5.4"


def test_resolve_upstream_model_supports_wildcard_alias():
    aliases = {"claude-sonnet*": "gpt-5.4", "claude-*": "gpt-5.4-mini"}
    resolved = resolve_upstream_model("claude-sonnet-4-5", "gpt-default", aliases)
    assert resolved == "gpt-5.4"
