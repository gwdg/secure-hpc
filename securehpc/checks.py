import logging
import os
import shutil
import subprocess
from pathlib import Path

from securehpc import config
from securehpc.config import Config, RunConfig

log = logging.getLogger(__name__)

CLIENT_TOOLS = ["gpg", "ssh", "scp", "sudo", "cryptsetup", "losetup", "mkfs.ext4", "mount", "umount", "vault"]


def check_client(cfg: Config) -> list[str]:
    if "PATH" not in os.environ:
        return ["PATH is not set"]
    return (
        check_tools()
        + check_placeholders(cfg)
        + check_secret_file(cfg.vault.token_file)
        + check_secret_file(cfg.container.private_key)
        + check_gpg_keys(cfg)
    )


def check_tools() -> list[str]:
    return [f"Tool not found in PATH: {tool}" for tool in CLIENT_TOOLS if shutil.which(tool) is None]


def check_placeholders(cfg: Config) -> list[str]:
    problems = []
    if cfg.cluster.user == "uXXXXX":
        problems.append(f"cluster.user is still the placeholder, edit {config.CONFIG_PATH}")
    return problems


def check_run(run_cfg: RunConfig) -> list[str]:
    problems = []
    if "uXXXXX" in run_cfg.exec_dir:
        problems.append("exec_dir in the run file is still the placeholder")
    if not run_cfg.data.is_dir():
        problems.append(f"Data folder not found: {run_cfg.data}")
    if not run_cfg.command.strip():
        problems.append("command in the run file is empty")
    return problems


def check_secret_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"File not found: {path}"]
    if path.stat().st_mode & 0o077:
        return [f"{path} is accessible by other users, run: chmod 600 {path}"]
    return []


def check_gpg_keys(cfg: Config) -> list[str]:
    if shutil.which("gpg") is None:
        return []  # already reported by check_tools
    problems = []
    if not _gpg_has_key("--list-keys", cfg.gpg.node_key):
        problems.append(f"Public key of the secure node not in GPG keyring: {cfg.gpg.node_key}")
    if not _gpg_has_key("--list-secret-keys", cfg.gpg.signing_key):
        problems.append(f"Your signing key not in GPG keyring: {cfg.gpg.signing_key}")
    return problems


def _gpg_has_key(list_option: str, key: str) -> bool:
    # gpg exits with 0 if the key exists. check=False: a missing key returns False instead of raising.
    result = subprocess.run(["gpg", list_option, key], check=False, capture_output=True)
    return result.returncode == 0
