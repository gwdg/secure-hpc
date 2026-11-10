import importlib.resources
import tomllib
from pathlib import Path

import pytest

from securehpc import checks
from securehpc.config import Config, RunConfig

DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()


def make_config(text: str = DEFAULT_TEXT) -> Config:
    return Config.from_dict(tomllib.loads(text))


def make_run(tmp_path: Path, **overrides: str) -> RunConfig:
    d = {
        "exec_dir": "/mnt/ceph-hdd/cold/u12345/secure",
        "container": "container.sif",
        "data": ".",
        "image_size_mb": 100,
        "command": "echo hi",
    }
    return RunConfig.from_dict(d | overrides, tmp_path)


def test_placeholders_reported() -> None:
    assert len(checks.check_placeholders(make_config())) == 1


def test_placeholders_replaced() -> None:
    assert checks.check_placeholders(make_config(DEFAULT_TEXT.replace("uXXXXX", "u12345"))) == []


def test_run_ok(tmp_path: Path) -> None:
    assert checks.check_run(make_run(tmp_path)) == []


def test_run_problems(tmp_path: Path) -> None:
    run_cfg = make_run(tmp_path, exec_dir="/x/uXXXXX/secure", data="nope", command="  \n")
    assert len(checks.check_run(run_cfg)) == 3


def test_secret_file_missing(tmp_path: Path) -> None:
    assert checks.check_secret_file(tmp_path / "nope") == [f"File not found: {tmp_path / 'nope'}"]


def test_secret_file_readable_by_others(tmp_path: Path) -> None:
    path = tmp_path / "token"
    path.write_text("x")
    path.chmod(0o644)
    assert "chmod 600" in checks.check_secret_file(path)[0]


def test_secret_file_private(tmp_path: Path) -> None:
    path = tmp_path / "token"
    path.write_text("x")
    path.chmod(0o600)
    assert checks.check_secret_file(path) == []


def test_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks, "CLIENT_TOOLS", ["sh", "securehpc-no-such-tool"])
    assert checks.check_tools() == ["Tool not found in PATH: securehpc-no-such-tool"]


def test_path_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PATH")
    assert checks.check_client(make_config()) == ["PATH is not set"]
