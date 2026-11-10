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
    exec_dir: str  # path on the cluster, so not a local Path
    reservation: str
    sbatch: str
    sacct: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClusterConfig":
        return cls(
            user=d["user"],
            login_node=d["login_node"],
            exec_dir=d["exec_dir"],
            reservation=d["reservation"],
            sbatch=d["sbatch"],
            sacct=d["sacct"],
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
