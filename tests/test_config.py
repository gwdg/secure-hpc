import importlib.resources
from pathlib import Path

import pytest

from securehpc import config
from securehpc.config import ConfigError

DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()


@pytest.fixture
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "securehpc" / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    return path


def test_ensure_config_creates_default(config_path: Path) -> None:
    config.ensure_config()
    assert config_path.read_text() == DEFAULT_TEXT


def test_ensure_config_keeps_existing(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True)
    config_path.write_text("mine")
    config.ensure_config()
    assert config_path.read_text() == "mine"


def test_default_config_loads(config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    config.ensure_config()
    cfg = config.load_config()
    assert cfg.vault.proxy is False
    assert cfg.vault.token_file == tmp_path / ".config" / "securehpc" / "vault.token"  # ~ expanded


def test_missing_key(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True)
    config_path.write_text(DEFAULT_TEXT.replace('reservation = "secure-hpc"\n', ""))
    with pytest.raises(ConfigError, match="reservation"):
        config.load_config()


def test_invalid_toml(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True)
    config_path.write_text("user = ")
    with pytest.raises(ConfigError, match="invalid TOML"):
        config.load_config()
