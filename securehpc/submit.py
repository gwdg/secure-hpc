"""The submit workflow, top to bottom in the order the steps run."""

import hashlib
import importlib.resources
import logging
import shlex
import sys
from pathlib import Path

from securehpc import checks, config, utils
from securehpc.config import Config, RunConfig

log = logging.getLogger(__name__)


def run(cfg: Config, run_file: Path, proxy: bool, debug_mode: bool) -> None:
    if debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)

    run_cfg = config.load_run(run_file)

    # Those checks are relevant enough to be run everytime
    problems = checks.check_client(cfg) + checks.check_run(run_cfg)
    for problem in problems:
        log.error(problem)
    if problems:
        log.error("%d problem(s) found, nothing was submitted", len(problems))
        sys.exit(1)

    # In case we are debugging with the user, this runs everything that could be a potential problem
    # (this is too much overhead to be run everytime though)
    if debug_mode:
        checks.run_debug_checks(cfg, run_cfg)

    utils.cache_sudo_credentials()
    close_previous()
    upload_container(cfg, run_cfg)
    log.info("submit (proxy=%s) is not implemented yet", proxy)


# ---------- LUKS image: carries the input data to the node and the results back ----------

NAME = "outdata"
MOUNT_POINT = Path("/mnt") / NAME
MAPPER = Path("/dev/mapper") / NAME


def close_previous() -> None:
    """Undo what the previous run left open: the mount, the LUKS mapping and its loop devices."""
    if MOUNT_POINT.is_mount():
        log.info("Unmounting the previous results at %s", MOUNT_POINT)
        utils.run(["sudo", "umount", str(MOUNT_POINT)])
    if MAPPER.exists():
        log.info("Closing the previous LUKS mapping %s", MAPPER)
        utils.run(["sudo", "cryptsetup", "luksClose", NAME])
    for device in _loop_devices():
        log.info("Detaching the previous loop device %s", device)
        utils.run(["sudo", "losetup", "--detach", device])


def _loop_devices() -> list[str]:
    """Loop devices backed by a file called outdata.img."""
    out = utils.run(["losetup", "--list", "--noheadings", "--output", "NAME,BACK-FILE"])
    devices = []
    for line in out.splitlines():
        device, _, back_file = line.strip().partition(" ")
        if Path(back_file.strip()).name == f"{NAME}.img":
            devices.append(device)
    return devices


# ---------- container ----------

REMOTE_CONTAINER = "container.sif"  # fixed name inside exec_dir, also hardcoded in command.sh.template


def upload_container(cfg: Config, run_cfg: RunConfig) -> None:
    """Upload the local container to exec_dir/container.sif, unless the same file is already there.

    Compares full sha256 hashes. A broken earlier upload has a different hash, so it is simply uploaded again.
    """
    remote = f"{run_cfg.exec_dir}/{REMOTE_CONTAINER}"
    with run_cfg.container.open("rb") as f:
        local_hash = hashlib.file_digest(f, "sha256").hexdigest()
    # prints nothing if the file does not exist yet
    out = utils.ssh(cfg, "sh", "-c", 'test ! -f "$1" || sha256sum "$1"', "sh", remote)
    remote_hash = out.split()[0] if out.strip() else None
    log.debug("Container hash: local %s, remote %s", local_hash, remote_hash)
    if remote_hash == local_hash:
        log.info("Container on the cluster is up to date")
        return

    size_mb = run_cfg.container.stat().st_size / 2**20
    log.info("Uploading %s (%.0f MB) to %s", run_cfg.container, size_mb, remote)
    # TODO: show progress. utils.run captures scp's output, so a big upload looks frozen.
    utils.run(["scp", str(run_cfg.container), f"{utils.ssh_target(cfg)}:{remote}"])


# ---------- job script ----------
# The job script: runs on the secure node, encrypted for the node and signed by the user.
#
# command.sh  the actual job, filled in from command.sh.template. Contains the Vault tokens,
#             so it only exists in memory and is encrypted via stdin.
# run.sh      what Slurm sees: passes the encrypted command.sh to the node's decrypt_and_execute.
# run.sh.sig  detached signature of run.sh, so the node can check it really comes from the user.


def write_jobscript(
    cfg: Config, run_cfg: RunConfig, default_token: str, wrapped_token: str, out_dir: Path
) -> tuple[Path, Path]:
    """Write run.sh and run.sh.sig into out_dir and return their paths."""
    run_sh = out_dir / "run.sh"
    run_sh.write_text(wrap(encrypt(cfg, render_command(cfg, run_cfg, default_token, wrapped_token))))
    return run_sh, sign(cfg, run_sh)


def render_command(cfg: Config, run_cfg: RunConfig, default_token: str, wrapped_token: str) -> str:
    text = (importlib.resources.files("securehpc") / "command.sh.template").read_text()
    values = {
        "<DEFAULT_TOKEN>": default_token,
        "<WRAPPED_TOKEN>": wrapped_token,
        "<EXEC_DIR>": run_cfg.exec_dir,
        "<VAULT_ADDR>": cfg.vault.address,
        "<VAULT_USER>": cfg.vault.user,
        "<CLUSTER_USER>": cfg.cluster.user,
        # last, so placeholder-like text inside the command is left alone
        "<COMMAND>": shlex.quote(run_cfg.command.strip()),
    }
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return text


def encrypt(cfg: Config, command_sh: str) -> str:
    return utils.run(
        ["gpg", "--batch", "--armor", "--trust-model", "always", "--recipient", cfg.gpg.node_key, "--encrypt"],
        input=command_sh,
    )


def wrap(encrypted: str) -> str:
    # no newline after the final EOF, exactly like the original
    return "#!/bin/bash\n/usr/bin/decrypt_and_execute <<EOF\n" + encrypted + "EOF"


def sign(cfg: Config, path: Path) -> Path:
    sig = path.with_name(path.name + ".sig")
    gpg = ["gpg", "--batch", "--yes", "--local-user", cfg.gpg.signing_key]
    utils.run([*gpg, "--output", str(sig), "--detach-sign", str(path)])
    return sig
