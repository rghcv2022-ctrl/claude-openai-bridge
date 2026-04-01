from fastapi.testclient import TestClient

from app import build_app, load_config


def test_load_config_reads_json_from_env(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            '{\n'
            '  "listen_host": "127.0.0.1",\n'
            '  "listen_port": 43118,\n'
            '  "upstream_base_url": "https://gmncode.cn/v1",\n'
            '  "upstream_api_key": "test-key",\n'
            '  "upstream_chat_path": "/chat/completions",\n'
            '  "default_model": "gpt-5.4",\n'
            '  "request_timeout_seconds": 30,\n'
            '  "log_level": "INFO",\n'
            '  "model_aliases": {\n'
            '    "claude-sonnet-4-5": "gpt-5.4"\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )
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
    config_path.write_text('{"listen_host":"127.0.0.1","listen_port":43118,"upstream_base_url":"https://gmncode.cn/v1","upstream_api_key":"k","upstream_chat_path":"/chat/completions","default_model":"gpt-5.4","request_timeout_seconds":30,"log_level":"INFO","model_aliases":{}}', encoding="utf-8")
    monkeypatch.delenv("CLAUDE_OPENAI_PROXY_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)

    cfg = load_config()
    assert cfg["listen_host"] == "127.0.0.1"
    assert cfg["listen_port"] == 43118


def test_healthz_reads_json_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            '{\n'
            '  "listen_host": "127.0.0.1",\n'
            '  "listen_port": 43118,\n'
            '  "upstream_base_url": "https://gmncode.cn/v1",\n'
            '  "upstream_api_key": "test-key",\n'
            '  "upstream_chat_path": "/chat/completions",\n'
            '  "default_model": "gpt-5.4",\n'
            '  "request_timeout_seconds": 30,\n'
            '  "log_level": "INFO",\n'
            '  "model_aliases": {\n'
            '    "claude-sonnet-4-5": "gpt-5.4"\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )
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
