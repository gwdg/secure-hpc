"""Checks before submitting.

Fast checks (check_client, check_run) run on every submit.
Debug checks (run_debug_checks) only run with `submit --debug`: slow on purpose,
they check everything that could break a run.

To add a debug check:
1. Write a function `my_check(cfg, run_cfg)` that raises an exception when something is wrong.
   Use utils.run or _ssh (both raise on failure and log the command), and log.debug anything useful.
2. Add one line to `run_debug_checks`.
"""

import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from securehpc import config, utils
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


# ---------- debug checks (submit --debug) ----------

SLURM_TOOLS = ["sbatch", "sacct", "scontrol", "squeue"]


def run_debug_checks(cfg: Config, run_cfg: RunConfig) -> None:
    # local
    _check("Data fits into the image", data_fits, cfg, run_cfg)
    _check("GPG can encrypt for the node and sign with your key", gpg_dummy_run, cfg, run_cfg)
    # cluster
    _check("SSH login to the frontend works", ssh_login, cfg, run_cfg)
    _check("Slurm tools are there", slurm_tools, cfg, run_cfg)
    _check("exec_dir exists", exec_dir_exists, cfg, run_cfg)
    _check("Container exists and is readable", container_readable, cfg, run_cfg)
    _check("Reservation exists and is usable", reservation_usable, cfg, run_cfg)
    _check("No job is running in the reservation", reservation_idle, cfg, run_cfg)
    # TODO: Vault checks: reachable (through the proxy with --proxy), token valid, remaining lifetime


def _check(name: str, check: Callable[[Config, RunConfig], None], cfg: Config, run_cfg: RunConfig) -> None:
    """Run one check. On failure, log why and stop the program: nothing is submitted."""
    log.info("Checking: %s", name)
    start = time.monotonic()
    try:
        check(cfg, run_cfg)
    except Exception as e:  # noqa: BLE001 - a broken check should show up as a failed check, not crash the run
        log.error("FAILED: %s: %s", name, e)
        log.error("Debug checks failed, nothing was submitted")
        sys.exit(1)
    log.info("ok: %s (%.1fs)", name, time.monotonic() - start)


def _ssh(cfg: Config, *cmd: str) -> str:
    """Run a command on the login node. BatchMode: fail instead of hanging on a password prompt."""
    target = f"{cfg.cluster.user}@{cfg.cluster.login_node}"
    return utils.run(["ssh", "-o", "BatchMode=yes", target, shlex.join(cmd)])


def _slurm(cfg: Config, tool: str) -> str:
    return f"{cfg.cluster.slurm_bin}/{tool}"


# --- local ---


def data_fits(cfg: Config, run_cfg: RunConfig) -> None:
    if not run_cfg.data.is_dir():
        raise RuntimeError(f"data folder not found: {run_cfg.data}")
    size = sum(p.stat().st_size for p in run_cfg.data.rglob("*") if p.is_file())
    log.debug("Data: %s, %.1f MB", run_cfg.data, size / 2**20)
    if size >= run_cfg.image_size_mb * 2**20:
        raise RuntimeError(f"data is {size / 2**20:.1f} MB, image_size_mb is {run_cfg.image_size_mb}")


def gpg_dummy_run(cfg: Config, run_cfg: RunConfig) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dummy = Path(tmp) / "dummy.txt"
        dummy.write_text("securehpc debug check\n")
        # the same options the real run uses
        encrypt = ["--armor", "--trust-model", "always", "--recipient", cfg.gpg.node_key, "--encrypt", str(dummy)]
        utils.run(["gpg", "--batch", *encrypt])
        utils.run(["gpg", "--batch", "--local-user", cfg.gpg.signing_key, "--detach-sign", str(dummy)])
        utils.run(["gpg", "--batch", "--verify", f"{dummy}.sig", str(dummy)])


# --- cluster ---


def ssh_login(cfg: Config, run_cfg: RunConfig) -> None:
    log.debug("Logged in as %s", _ssh(cfg, "whoami").strip())


def slurm_tools(cfg: Config, run_cfg: RunConfig) -> None:
    for tool in SLURM_TOOLS:
        log.debug(_ssh(cfg, _slurm(cfg, tool), "--version").strip())


def exec_dir_exists(cfg: Config, run_cfg: RunConfig) -> None:
    kind, owner, mode = _ssh(cfg, "stat", "-c", "%F %U %a", run_cfg.exec_dir).rsplit(maxsplit=2)
    log.debug("exec_dir: %s, owner %s, mode %s", kind, owner, mode)
    if kind != "directory":
        raise RuntimeError(f"{run_cfg.exec_dir} is a {kind}, not a directory")


def container_readable(cfg: Config, run_cfg: RunConfig) -> None:
    path = f"{run_cfg.exec_dir}/{run_cfg.container}"
    size = int(_ssh(cfg, "stat", "-c", "%s", path))
    log.debug("Container: %s, %.1f MB", path, size / 2**20)
    _ssh(cfg, "head", "-c", "1", path)  # fails with "Permission denied" if not readable


def reservation_usable(cfg: Config, run_cfg: RunConfig) -> None:
    out = _ssh(cfg, _slurm(cfg, "scontrol"), "show", "reservation", cfg.cluster.reservation)
    fields = parse_scontrol(out)
    if fields.get("ReservationName") != cfg.cluster.reservation:
        raise RuntimeError(f"reservation not found: {out.strip()}")
    log.debug(
        "Reservation: nodes %s, state %s, ends %s", fields.get("Nodes"), fields.get("State"), fields.get("EndTime")
    )
    if fields.get("State") != "ACTIVE":
        raise RuntimeError(f"reservation is {fields.get('State')}, not ACTIVE")
    users = fields.get("Users", "(null)")
    if users != "(null)" and cfg.cluster.user not in users.split(","):
        raise RuntimeError(f"{cfg.cluster.user} is not in the reservation's users: {users}")


def parse_scontrol(out: str) -> dict[str, str]:
    """`Key=Value Key=Value ...` output of scontrol, as a dict."""
    return dict(item.split("=", 1) for item in out.split() if "=" in item)


def reservation_idle(cfg: Config, run_cfg: RunConfig) -> None:
    jobs = _ssh(
        cfg, _slurm(cfg, "squeue"), "--noheader", f"--reservation={cfg.cluster.reservation}", "--format=%i %u %T"
    )
    if jobs.strip():
        raise RuntimeError(f"jobs in the reservation (job id, user, state):\n{jobs.rstrip()}")
