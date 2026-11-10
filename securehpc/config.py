import importlib.resources
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".config" / "securehpc" / "config.toml"


@dataclass(frozen=True)
class ClusterConfig:
    user: str
    login_node: str
    reservation: str
    slurm_bin: str  # path on the login node

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClusterConfig":
        return cls(
            user=d["user"],
            login_node=d["login_node"],
            reservation=d["reservation"],
            slurm_bin=d["slurm_bin"],
        )


@dataclass(frozen=True)
class VaultConfig:
    address: str
    user: str
    token_file: Path

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VaultConfig":
        return cls(
            address=d["address"],
            user=d["user"],
            token_file=Path(d["token_file"]).expanduser(),
        )


@dataclass(frozen=True)
class GpgConfig:
    node_key: str
    signing_key: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GpgConfig":
        return cls(node_key=d["node_key"], signing_key=d["signing_key"])


@dataclass(frozen=True)
class ContainerConfig:
    private_key: Path

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ContainerConfig":
        return cls(private_key=Path(d["private_key"]).expanduser())


@dataclass(frozen=True)
class Config:
    cluster: ClusterConfig
    vault: VaultConfig
    gpg: GpgConfig
    container: ContainerConfig

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Config":
        return cls(
            cluster=ClusterConfig.from_dict(d["cluster"]),
            vault=VaultConfig.from_dict(d["vault"]),
            gpg=GpgConfig.from_dict(d["gpg"]),
            container=ContainerConfig.from_dict(d["container"]),
        )


@dataclass(frozen=True)
class RunConfig:
    """One job, read from a run.toml."""

    exec_dir: str  # folder on the cluster, so not a local Path
    container: str  # file name inside exec_dir
    data: Path
    image_size_mb: int
    command: str

    @classmethod
    def from_dict(cls, d: dict[str, Any], base_dir: Path) -> "RunConfig":
        return cls(
            exec_dir=d["exec_dir"],
            container=d["container"],
            data=base_dir / Path(d["data"]).expanduser(),  # relative to the run.toml, absolute stays absolute
            image_size_mb=d["image_size_mb"],
            command=d["command"],
        )


class ConfigError(Exception):
    pass


def ensure_config() -> None:
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    default = importlib.resources.files("securehpc") / "default_config.toml"
    CONFIG_PATH.write_text(default.read_text())
    log.warning("No config found, created a default one at %s. Please edit it.", CONFIG_PATH)


def load_config() -> Config:
    try:
        with CONFIG_PATH.open("rb") as f:
            return Config.from_dict(tomllib.load(f))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{CONFIG_PATH}: invalid TOML: {e}") from e
    except KeyError as e:
        raise ConfigError(f"{CONFIG_PATH}: missing key {e}") from e


def load_run(path: Path) -> RunConfig:
    try:
        with path.open("rb") as f:
            return RunConfig.from_dict(tomllib.load(f), path.parent)
    except FileNotFoundError as e:
        raise ConfigError(f"{path}: file not found") from e
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: invalid TOML: {e}") from e
    except KeyError as e:
        raise ConfigError(f"{path}: missing key {e}") from e
