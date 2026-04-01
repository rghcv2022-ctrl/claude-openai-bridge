import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_stop_proxy_script_removes_pid_file_without_pid_variable_conflict(tmp_path):
    temp_root = tmp_path / "proxy"
    scripts_dir = temp_root / "scripts"
    run_dir = temp_root / "run"
    scripts_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)

    source_script = PROJECT_ROOT / "scripts" / "stop-proxy.ps1"
    temp_script = scripts_dir / "stop-proxy.ps1"
    shutil.copyfile(source_script, temp_script)
    (run_dir / "proxy.pid").write_text("999999", encoding="ascii")

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(temp_script),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not (run_dir / "proxy.pid").exists()
    assert "Proxy stopped: 999999" in result.stdout
