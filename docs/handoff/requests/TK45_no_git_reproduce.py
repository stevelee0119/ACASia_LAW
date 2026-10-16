"""Reproduce the public TK45 controls without Git metadata or network work."""
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
TESTS = (
    "test_tk45_native_format_admission.py",
    "test_tk45_norm_binding_capability_spike.py",
    "test_tk45_norm_legal_admission_spike.py",
)


def main():
    with tempfile.TemporaryDirectory(prefix="tk45-public-no-git-") as directory:
        target = Path(directory)
        for folder in ("packages", "apps", "config", "scripts"):
            shutil.copytree(ROOT / folder, target / folder,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (target / "tests").mkdir()
        for name in TESTS + ("conftest.py", "tk45_norm_binding_capability.py", "tk45_f8_source_delta_baseline.py"):
            shutil.copy2(ROOT / "tests" / name, target / "tests" / name)
        shutil.copy2(ROOT / "pytest.ini", target / "pytest.ini")
        assert not (target / ".git").exists()
        print(json.dumps({"git_metadata_present": False, "python": platform.python_version(),
                          "platform": platform.system(), "public_snapshot_only": True}), flush=True)
        subprocess.run([sys.executable, "-m", "pytest", *("tests/" + name for name in TESTS),
                        "--tb=short"], cwd=target, check=True)


if __name__ == "__main__":
    main()
