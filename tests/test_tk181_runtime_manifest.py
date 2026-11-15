"""TK-181 R1/R5/R6 검증: 실행 환경 런타임 기록, 잠금 파일 해시, pytest 운영 제외."""
from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

from packages.verification_engine import environment as env_mod


ROOT = Path(__file__).resolve().parents[1]


def test_preflight_records_runtime_python_os_and_packages():
    result = env_mod.preflight()
    runtime = result.get("runtime")
    assert isinstance(runtime, dict)
    assert isinstance(runtime.get("python"), str) and runtime["python"]
    assert isinstance(runtime.get("os"), str)
    packages = runtime.get("packages")
    assert isinstance(packages, dict)
    assert set(packages) == set(env_mod.RUNTIME_PACKAGES)
    assert packages["fastapi"]


def test_fingerprint_ignores_runtime_differences():
    base = env_mod.preflight()
    altered = {
        **base,
        "runtime": {
            "python": "3.99.0",
            "os": "OtherOS",
            "packages": {name: "0.0.0" for name in env_mod.RUNTIME_PACKAGES},
        },
    }
    assert env_mod.fingerprint(base) == env_mod.fingerprint(altered)


def test_runtime_info_uses_empty_string_when_package_missing(monkeypatch):
    real_version = importlib.metadata.version

    def fake_version(name: str) -> str:
        if name == "pypdfium2":
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)

    monkeypatch.setattr(env_mod.importlib.metadata, "version", fake_version)
    runtime = env_mod._runtime_info()
    assert runtime["packages"]["pypdfium2"] == ""
    assert runtime["packages"]["fastapi"] != ""


def test_runtime_requirements_exclude_pytest_and_include_hashes():
    req_in = (ROOT / "requirements.in").read_text(encoding="utf-8")
    req_txt = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    req_test_in = (ROOT / "requirements-test.in").read_text(encoding="utf-8")
    req_test_txt = (ROOT / "requirements-test.txt").read_text(encoding="utf-8")

    assert not re.search(r"(?m)^\s*pytest\b", req_in)
    assert not re.search(r"(?m)^pytest==", req_txt)
    assert "olefile<0.48" in req_in or "olefile>=0.47,<0.48" in req_in
    assert "celery" in req_in and "redis" in req_in
    assert "--hash=sha256:" in req_txt

    assert re.search(r"(?m)^\s*pytest\b", req_test_in)
    assert re.search(r"(?m)^pytest==", req_test_txt)
    assert "--hash=sha256:" in req_test_txt


def test_dockerfile_requires_hashes():
    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert "--require-hashes" in dockerfile


def test_workflows_install_hashed_test_requirements():
    for rel_path in (".github/workflows/score-gate.yml", ".github/workflows/live-integration.yml"):
        content = (ROOT / rel_path).read_text(encoding="utf-8")
        assert re.search(
            r"pip\s+install\s+--require-hashes\s+-r\s+requirements-test\.txt",
            content,
        ), f"{rel_path} must install requirements-test.txt with --require-hashes"

