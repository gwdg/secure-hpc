"""The submit workflow, top to bottom in the order the steps run."""

import hashlib
import importlib.resources
import logging
import os
import secrets
import shlex
import shutil
import string
import sys
from pathlib import Path

from securehpc import checks, config, utils
from securehpc.config import Config, RunConfig

log = logging.getLogger(__name__)


def run(cfg: Config, run_file: Path, proxy: bool, debug_mode: bool) -> None:
    if debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)

    run_file = run_file.resolve()  # absolute, so printed paths work from any folder
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
    create_image(run_cfg, run_file.parent)
    upload_image(cfg, run_cfg, run_file.parent)
    upload_container(cfg, run_cfg)
    log.info("submit (proxy=%s) is not implemented yet", proxy)
    log.info("%s", mount_command(run_file.parent))


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


def create_image(run_cfg: RunConfig, job_dir: Path) -> None:
    """Create job_dir/outdata.img, encrypted with a new job_dir/outdata.key, with the input data inside.

    No losetup, unlike the original: cryptsetup formats the file directly, and luksOpen on a file
    attaches its own loop device and detaches it again on luksClose.
    """
    image = job_dir / f"{NAME}.img"
    key = job_dir / f"{NAME}.key"
    if image.exists():
        log.warning("Overwriting %s and its key from the previous run", image)
    log.info("Creating the encrypted image %s (%d MB)", image, run_cfg.image_size_mb)

    with image.open("wb") as f:
        f.truncate(run_cfg.image_size_mb * 2**20)  # all zeros, like dd if=/dev/zero bs=1M
    _write_key(key)

    utils.run(
        ["sudo", "cryptsetup", "--batch-mode", "-c", "aes-xts-plain", "-s", "512", "luksFormat", str(image), str(key)]
    )
    utils.run(["sudo", "cryptsetup", "luksOpen", str(image), NAME, "--key-file", str(key)])
    utils.run(["sudo", "mkfs.ext4", str(MAPPER)])
    utils.run(["sudo", "mkdir", "-p", str(MOUNT_POINT)])
    utils.run(["sudo", "mount", "-t", "ext4", str(MAPPER), str(MOUNT_POINT)])
    utils.run(["sudo", "chown", "-R", str(os.getuid()), str(MOUNT_POINT)])

    # as the user, no sudo needed after the chown
    shutil.copytree(run_cfg.data, MOUNT_POINT, dirs_exist_ok=True)

    utils.run(["sudo", "umount", str(MOUNT_POINT)])
    utils.run(["sudo", "cryptsetup", "luksClose", NAME])


def upload_image(cfg: Config, run_cfg: RunConfig, job_dir: Path) -> None:
    """Upload outdata.img to exec_dir, where the node's mount_data expects it."""
    remote = f"{run_cfg.exec_dir}/{NAME}.img"
    log.info("Uploading the encrypted image to %s", remote)
    utils.run(["scp", str(job_dir / f"{NAME}.img"), f"{utils.ssh_target(cfg)}:{remote}"])


def mount_command(job_dir: Path) -> str:
    """Shell commands to open and close the image, like old/utils/mount_data.sh, as markdown code blocks.

    The next submit closes it again.
    """
    image, key = shlex.quote(str(job_dir / f"{NAME}.img")), shlex.quote(str(job_dir / f"{NAME}.key"))
    return (
        "To open the image:\n"
        "```bash\n"
        f"sudo cryptsetup luksOpen {image} {NAME} --key-file {key} && "
        f"sudo mkdir -p {MOUNT_POINT} && "
        f"sudo mount -o rw,noexec,nosuid,nodev {MAPPER} {MOUNT_POINT} && "
        f"sudo chown -R $(id -u) {MOUNT_POINT}\n"
        "```\n"
        "To close it again:\n"
        "```bash\n"
        f"sudo umount {MOUNT_POINT} && sudo cryptsetup luksClose {NAME}\n"
        "```"
    )


def _write_key(path: Path) -> None:
    """32 random characters from 0-9a-zA-Z, like the original, but only readable by the user."""
    alphabet = string.ascii_letters + string.digits
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)  # an existing key file keeps its old mode otherwise
    with os.fdopen(fd, "w") as f:
        f.write("".join(secrets.choice(alphabet) for _ in range(32)))


def _loop_devices() -> list[str]:
    """Loop devices backed by a file called outdata.img."""
    out = utils.run(["sudo", "losetup", "--list", "--noheadings", "--output", "NAME,BACK-FILE"])
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
