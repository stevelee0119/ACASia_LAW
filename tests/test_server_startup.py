"""The deployment command must not depend on a platform's shell quoting."""
import json
import subprocess
from pathlib import Path

import pytest

from scripts import start_server


@pytest.fixture
def launch(monkeypatch):
    for name in ("PORT", "RENDER_SERVICE_ID", "FORWARDED_ALLOW_IPS"):
        monkeypatch.delenv(name, raising=False)
    calls = []
    monkeypatch.setattr(start_server.sys, "executable", "/path with spaces/python")
    monkeypatch.setattr(
        start_server.subprocess, "run",
        lambda args, **kwargs: calls.append(("migration", args, kwargs)),
    )
    monkeypatch.setattr(
        start_server.os, "execv",
        lambda executable, args: calls.append(("server", executable, args)),
    )
    return calls


@pytest.mark.parametrize("port,expected", [(None, "8000"), ("10000", "10000"), ("19123", "19123")])
def test_migrate_before_server_with_explicit_arguments(monkeypatch, launch, port, expected):
    if port is not None:
        monkeypatch.setenv("PORT", port)
    assert start_server.main() == 0
    assert launch == [
        ("migration", ["/path with spaces/python", "-m", "alembic", "upgrade", "head"], {"check": True, "timeout": 120}),
        ("server", "/path with spaces/python", [
            "/path with spaces/python", "-m", "uvicorn", "apps.api.main:app",
            "--host", "0.0.0.0", "--port", expected,
            "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1",
        ]),
    ]


@pytest.mark.parametrize("port", ["", "$PORT", "0", "-1", "65536", "abc", "10000 && echo bad"])
def test_invalid_port_does_not_migrate_or_launch(monkeypatch, launch, capsys, port):
    monkeypatch.setenv("PORT", port)
    assert start_server.main() == 2
    assert not launch
    assert "PORT must be an integer" in capsys.readouterr().err


@pytest.mark.parametrize("exit_code,expected", [(1, 1), (7, 7), (-15, 1)])
def test_migration_failure_prevents_server(monkeypatch, launch, capsys, exit_code, expected):
    def fail(args, **kwargs):
        raise subprocess.CalledProcessError(exit_code, args)
    monkeypatch.setattr(start_server.subprocess, "run", fail)
    assert start_server.main() == expected
    assert not launch
    assert "API was not started" in capsys.readouterr().err


def test_migration_timeout_prevents_server(monkeypatch, launch, capsys):
    def timeout(args, **kwargs):
        assert kwargs["timeout"] == 120
        raise subprocess.TimeoutExpired(args, 120)
    monkeypatch.setattr(start_server.subprocess, "run", timeout)
    assert start_server.main() == 1
    assert not launch
    assert "timed out after 120 seconds; API was not started" in capsys.readouterr().err


@pytest.mark.parametrize("explicit,expected", [(None, "*"), ("10.0.0.0/8", "10.0.0.0/8"), ("", "")])
def test_render_proxy_trust_respects_explicit_override(monkeypatch, launch, explicit, expected):
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")
    if explicit is not None:
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", explicit)
    start_server.main()
    assert launch[-1][2][-1] == expected


def test_deployment_configs_share_shell_free_entrypoint():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "docker/Dockerfile").read_text(encoding="utf-8")
    command = next(line.removeprefix("CMD ") for line in dockerfile.splitlines() if line.startswith("CMD "))
    assert json.loads(command) == ["python", "-m", "scripts.start_server"]
    blueprint = (root / "render.yaml").read_text(encoding="utf-8")
    assert "dockerCommand: python -m scripts.start_server" in blueprint


def test_dockerfile_appuser_in_render_secret_group_1000():
    """운영 컨테이너 appuser가 Render Secret File(GID 1000) 그룹에 속하는지 정적 검사 (TK-79, 한국어 주석)."""
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "docker/Dockerfile").read_text(encoding="utf-8")
    lines = dockerfile.splitlines()

    # GID 1000 그룹 생성 및 appuser의 GID 1000 보조 그룹 추가 확인
    assert any("group 1000" in line for line in lines), "GID 1000 그룹 확인/생성 명령이 Dockerfile에 있어야 합니다."
    assert any("10001" in line and "1000" in line for line in lines), "appuser(UID 10001)에 GID 1000 그룹이 부여되어야 합니다."

    # USER appuser 전환 이전에 그룹 추가가 완료되어야 함
    user_line_idx = next(i for i, line in enumerate(lines) if line.strip() == "USER appuser")
    group_line_idx = next(i for i, line in enumerate(lines) if "1000" in line and "appuser" in line)
    assert group_line_idx < user_line_idx, "USER appuser 전환 전에 그룹 추가 및 사용자 생성이 완료되어야 합니다."
