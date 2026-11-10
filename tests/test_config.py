import importlib.resources
from pathlib import Path

import pytest

from securehpc import config
from securehpc.config import ConfigError, RunConfig

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


RUN_TOML = """
exec_dir = "/mnt/ceph-hdd/cold/u12345/secure"
container = "container.sif"
data = "./data"
image_size_mb = 100
command = "echo hi"
"""


def test_load_run_data_relative_to_file(tmp_path: Path) -> None:
    path = tmp_path / "project" / "run.toml"
    path.parent.mkdir()
    path.write_text(RUN_TOML)
    run_cfg = config.load_run(path)
    assert run_cfg == RunConfig(
        exec_dir="/mnt/ceph-hdd/cold/u12345/secure",
        container="container.sif",
        data=tmp_path / "project" / "data",
        image_size_mb=100,
        command="echo hi",
    )


def test_load_run_absolute_data(tmp_path: Path) -> None:
    path = tmp_path / "run.toml"
    path.write_text(RUN_TOML.replace('"./data"', '"/srv/data"'))
    assert config.load_run(path).data == Path("/srv/data")


def test_load_run_missing_key(tmp_path: Path) -> None:
    path = tmp_path / "run.toml"
    path.write_text(RUN_TOML.replace('command = "echo hi"', ""))
    with pytest.raises(ConfigError, match="command"):
        config.load_run(path)


def test_load_run_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="file not found"):
        config.load_run(tmp_path / "run.toml")
