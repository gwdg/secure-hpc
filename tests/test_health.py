import importlib.resources
import tomllib
from pathlib import Path

import pytest

from securehpc import health
from securehpc.config import Config

DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()


def make_config(text: str = DEFAULT_TEXT) -> Config:
    return Config.from_dict(tomllib.loads(text))


def test_placeholders_reported() -> None:
    problems = health.check_placeholders(make_config())
    assert len(problems) == 2


def test_placeholders_replaced() -> None:
    text = DEFAULT_TEXT.replace("uXXXXX", "u12345").replace("your_path", "u12345/secure")
    assert health.check_placeholders(make_config(text)) == []


def test_secret_file_missing(tmp_path: Path) -> None:
    assert health.check_secret_file(tmp_path / "nope") == [f"File not found: {tmp_path / 'nope'}"]


def test_secret_file_readable_by_others(tmp_path: Path) -> None:
    path = tmp_path / "token"
    path.write_text("x")
    path.chmod(0o644)
    assert "chmod 600" in health.check_secret_file(path)[0]


def test_secret_file_private(tmp_path: Path) -> None:
    path = tmp_path / "token"
    path.write_text("x")
    path.chmod(0o600)
    assert health.check_secret_file(path) == []


def test_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "CLIENT_TOOLS", ["sh", "securehpc-no-such-tool"])
    assert health.check_tools() == ["Tool not found in PATH: securehpc-no-such-tool"]


def test_path_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PATH")
    assert health.check_client(make_config()) == ["PATH is not set"]
