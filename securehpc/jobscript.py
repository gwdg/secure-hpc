"""The job script: runs on the secure node, encrypted for the node and signed by the user.

command.sh  the actual job, filled in from command.sh.template. Contains the Vault tokens,
            so it only exists in memory and is encrypted via stdin.
run.sh      what Slurm sees: passes the encrypted command.sh to the node's decrypt_and_execute.
run.sh.sig  detached signature of run.sh, so the node can check it really comes from the user.
"""

import importlib.resources
import shlex
from pathlib import Path

from securehpc import shell
from securehpc.config import Config, RunConfig


def write(cfg: Config, run_cfg: RunConfig, default_token: str, wrapped_token: str, out_dir: Path) -> tuple[Path, Path]:
    """Write run.sh and run.sh.sig into out_dir and return their paths."""
    run_sh = out_dir / "run.sh"
    run_sh.write_text(wrap(encrypt(cfg, render(cfg, run_cfg, default_token, wrapped_token))))
    return run_sh, sign(cfg, run_sh)


def render(cfg: Config, run_cfg: RunConfig, default_token: str, wrapped_token: str) -> str:
    text = (importlib.resources.files("securehpc") / "command.sh.template").read_text()
    values = {
        "<DEFAULT_TOKEN>": default_token,
        "<WRAPPED_TOKEN>": wrapped_token,
        "<EXEC_DIR>": run_cfg.exec_dir,
        "<VAULT_ADDR>": cfg.vault.address,
        "<VAULT_USER>": cfg.vault.user,
        "<CLUSTER_USER>": cfg.cluster.user,
        "<CONTAINER>": run_cfg.container,
        # last, so placeholder-like text inside the command is left alone
        "<COMMAND>": shlex.quote(run_cfg.command.strip()),
    }
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return text


def encrypt(cfg: Config, command_sh: str) -> str:
    return shell.run(
        ["gpg", "--batch", "--armor", "--trust-model", "always", "--recipient", cfg.gpg.node_key, "--encrypt"],
        input=command_sh,
    )


def wrap(encrypted: str) -> str:
    # no newline after the final EOF, exactly like the original
    return "#!/bin/bash\n/usr/bin/decrypt_and_execute <<EOF\n" + encrypted + "EOF"


def sign(cfg: Config, path: Path) -> Path:
    sig = path.with_name(path.name + ".sig")
    gpg = ["gpg", "--batch", "--yes", "--local-user", cfg.gpg.signing_key]
    shell.run([*gpg, "--output", str(sig), "--detach-sign", str(path)])
    return sig
