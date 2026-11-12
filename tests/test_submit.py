import hashlib
import importlib.resources
import os
import shlex
import subprocess
import tempfile
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

from securehpc import submit, utils
from securehpc.config import Config, RunConfig
from securehpc.utils import CommandError

ASSETS = Path(__file__).parent / "assets"
DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()

# the values the original client had hardcoded or was called with when the assets were generated
ORIGINAL_COMMAND = 'echo "In the input file was: \\"$(cat /output/input.txt)\\"" > /output/output.txt'

LOSETUP_OUT = """\
/dev/loop0 /home/me/securehpc/outdata.img
/dev/loop1 /var/lib/snapd/snaps/core_123.snap
/dev/loop2 /home/me/other/outdata.img.bak
/dev/loop3 /tmp/outdata.img
"""


def make_original_config() -> Config:
    return Config.from_dict(tomllib.loads(DEFAULT_TEXT.replace("uXXXXX", "u19997")))


def make_original_run(command: str = ORIGINAL_COMMAND) -> RunConfig:
    d = {
        "exec_dir": "/mnt/ceph-hdd/cold/u19997/secure",
        "container": "container.sif",
        "data": ".",
        "image_size_mb": 100,
        "command": command,
    }
    return RunConfig.from_dict(d, Path("."))


# ---------- LUKS image ----------


def fake_run(calls: list[list[str]]):
    def run(cmd: list[str], input: str | None = None) -> str:
        calls.append(cmd)
        return LOSETUP_OUT if cmd[:3] == ["sudo", "losetup", "--list"] else ""

    return run


def test_loop_devices_only_outdata_img(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "run", fake_run([]))
    assert submit._loop_devices() == ["/dev/loop0", "/dev/loop3"]


def test_close_previous_undoes_everything(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(utils, "run", fake_run(calls))
    monkeypatch.setattr(submit, "MOUNT_POINT", Path("/"))  # always a mount point
    monkeypatch.setattr(submit, "MAPPER", tmp_path)  # exists
    submit.close_previous()
    assert [c for c in calls if c[1] != "losetup" or c[2] != "--list"] == [
        ["sudo", "umount", "/"],
        ["sudo", "cryptsetup", "luksClose", "outdata"],
        ["sudo", "losetup", "--detach", "/dev/loop0"],
        ["sudo", "losetup", "--detach", "/dev/loop3"],
    ]


def test_close_previous_nothing_to_do(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(utils, "run", lambda cmd, input=None: calls.append(cmd) or "")
    monkeypatch.setattr(submit, "MOUNT_POINT", tmp_path)  # not a mount point
    monkeypatch.setattr(submit, "MAPPER", tmp_path / "nope")
    submit.close_previous()
    assert calls == [["sudo", "losetup", "--list", "--noheadings", "--output", "NAME,BACK-FILE"]]


def test_write_key(tmp_path: Path) -> None:
    key = tmp_path / "outdata.key"
    key.write_text("old")
    key.chmod(0o644)
    submit._write_key(key)
    text = key.read_text()
    assert len(text) == 32 and text.isascii() and text.isalnum()
    assert key.stat().st_mode & 0o777 == 0o600


def test_mount_command() -> None:
    assert submit.mount_command(Path("/my jobs/a")).splitlines() == [
        "To open the image:",
        "```bash",
        (
            "sudo cryptsetup luksOpen '/my jobs/a/outdata.img' outdata --key-file '/my jobs/a/outdata.key' && "
            "sudo mkdir -p /mnt/outdata && "
            "sudo mount -o rw,noexec,nosuid,nodev /dev/mapper/outdata /mnt/outdata && "
            "sudo chown -R $(id -u) /mnt/outdata"
        ),
        "```",
        "To close it again:",
        "```bash",
        "sudo umount /mnt/outdata && sudo cryptsetup luksClose outdata",
        "```",
    ]


def test_create_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(utils, "run", lambda cmd, input=None: calls.append(cmd) or "")
    mount_point = tmp_path / "mnt"
    mount_point.mkdir()  # the fake mount: a plain folder
    monkeypatch.setattr(submit, "MOUNT_POINT", mount_point)
    data = tmp_path / "data"
    (data / "sub").mkdir(parents=True)
    (data / "input.txt").write_text("hello")
    (data / "sub" / ".hidden").write_text("too")
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    run_cfg = RunConfig("/x", tmp_path / "c.sif", data, 3, "true")

    submit.create_image(run_cfg, job_dir)

    image, key, mnt = str(job_dir / "outdata.img"), str(job_dir / "outdata.key"), str(mount_point)
    assert calls == [
        ["sudo", "cryptsetup", "--batch-mode", "-c", "aes-xts-plain", "-s", "512", "luksFormat", image, key],
        ["sudo", "cryptsetup", "luksOpen", image, "outdata", "--key-file", key],
        ["sudo", "mkfs.ext4", "/dev/mapper/outdata"],
        ["sudo", "mkdir", "-p", mnt],
        ["sudo", "mount", "-t", "ext4", "/dev/mapper/outdata", mnt],
        ["sudo", "chown", "-R", str(os.getuid()), mnt],
        ["sudo", "umount", mnt],
        ["sudo", "cryptsetup", "luksClose", "outdata"],
    ]
    assert (job_dir / "outdata.img").stat().st_size == 3 * 2**20
    assert (mount_point / "input.txt").read_text() == "hello"
    assert (mount_point / "sub" / ".hidden").read_text() == "too"


def test_upload_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(utils, "run", lambda cmd, input=None: calls.append(cmd) or "")
    submit.upload_image(make_original_config(), make_original_run(), tmp_path)
    assert calls == [
        [
            "scp",
            str(tmp_path / "outdata.img"),
            "u19997@glogin7.hpc.gwdg.de:/mnt/ceph-hdd/cold/u19997/secure/outdata.img",
        ]
    ]


# ---------- container ----------


def upload_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, remote_out: str) -> list[list[str]]:
    """Run upload_container against a fake cluster whose sha256sum prints remote_out; return the scp calls."""
    calls: list[list[str]] = []

    def run(cmd: list[str], input: str | None = None) -> str:
        calls.append(cmd)
        return remote_out if cmd[0] == "ssh" else ""

    monkeypatch.setattr(utils, "run", run)
    (tmp_path / "container.sif").write_bytes(b"container")
    run_cfg = make_original_run()
    run_cfg = RunConfig.from_dict({**vars(run_cfg), "data": ".", "container": "container.sif"}, tmp_path)
    submit.upload_container(make_original_config(), run_cfg)
    return [c for c in calls if c[0] == "scp"]


CONTAINER_SHA256 = hashlib.sha256(b"container").hexdigest()


def test_upload_container_same_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    remote = f"{CONTAINER_SHA256}  /mnt/ceph-hdd/cold/u19997/secure/container.sif\n"
    assert upload_calls(monkeypatch, tmp_path, remote) == []


def test_upload_container_other_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    remote = f"{'0' * 64}  /mnt/ceph-hdd/cold/u19997/secure/container.sif\n"
    assert upload_calls(monkeypatch, tmp_path, remote) == [
        [
            "scp",
            str(tmp_path / "container.sif"),
            "u19997@glogin7.hpc.gwdg.de:/mnt/ceph-hdd/cold/u19997/secure/container.sif",
        ]
    ]


def test_upload_container_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert len(upload_calls(monkeypatch, tmp_path, "")) == 1


# ---------- Vault ----------

VAULT_ENV = {"VAULT_ADDR": "https://kms.hpc.gwdg.de", "VAULT_TOKEN": "hvs.MY-TOKEN"}


def vault_calls(monkeypatch: pytest.MonkeyPatch, out: str = "") -> list[tuple[list[str], dict[str, str] | None]]:
    calls: list[tuple[list[str], dict[str, str] | None]] = []

    def run(cmd: list[str], input: str | None = None, env: dict[str, str] | None = None) -> str:
        calls.append((cmd, env))
        return out

    monkeypatch.setattr(utils, "run", run)
    return calls


def test_store_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = vault_calls(monkeypatch)
    cfg = make_original_config()
    submit.store_keys(cfg, VAULT_ENV, tmp_path)
    # the same paths as old/prepare_scripts.sh, values read from the files by vault itself
    assert calls == [
        (
            [
                "vault",
                "kv",
                "put",
                "-tls-skip-verify",
                "secret/data/user_2/outdata",
                f"key=@{tmp_path / 'outdata.key'}",
            ],
            VAULT_ENV,
        ),
        (
            [
                "vault",
                "kv",
                "put",
                "-tls-skip-verify",
                "secret/data/user_2/rsa_pri",
                f"key=@{cfg.container.private_key}",
            ],
            VAULT_ENV,
        ),
    ]


def test_create_wrapped_token(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = vault_calls(monkeypatch, out="hvs.WRAPPED\n")
    assert submit.create_wrapped_token(make_original_config(), VAULT_ENV) == "hvs.WRAPPED"
    assert calls == [
        (
            [
                "vault",
                "token",
                "create",
                "-tls-skip-verify",
                "-policy=user_2-node",
                "-wrap-ttl=3000",
                "-use-limit=3",
                "-field=wrapping_token",
            ],
            VAULT_ENV,
        )
    ]


# ---------- job script ----------


# The original's command.sh, minus the unused single-use token (set but never exported; the job works
# without it, tested on the cluster) and minus a stale TODO (the username now comes from the config).
# Everything else stays byte-for-byte the same.
EXPECTED_COMMAND_SH = (
    (ASSETS / "command.sh")
    .read_text()
    .replace("token_setup=hvs.DUMMY-DEFAULT-TOKEN\n", "")
    .replace("VAULT_TOKEN=$token_setup\n", "")
    .replace("# TODO: Do not hard code the username here\n", "")
)


def render(command: str = ORIGINAL_COMMAND) -> str:
    return submit.render_command(make_original_config(), make_original_run(command), "hvs.DUMMY-WRAPPED-TOKEN")


def test_render_matches_original() -> None:
    assert render() == EXPECTED_COMMAND_SH


def test_render_ignores_surrounding_newlines() -> None:
    # a TOML multi-line string ends with a newline
    assert render(f"\n{ORIGINAL_COMMAND}\n") == EXPECTED_COMMAND_SH


@pytest.mark.parametrize("command", ["echo 'single quotes'", 'a && b; echo "$HOME" | tr a b', "line1\nline2"])
def test_render_command_survives_quoting(command: str) -> None:
    # the first shell word after "bash -c" must be exactly the command
    after_bash_c = render(command).split("bash -c ", 1)[1]
    assert shlex.split(after_bash_c)[0] == command


def test_wrap_matches_original() -> None:
    assert submit.wrap((ASSETS / "command.sh.asc").read_text()) == (ASSETS / "run.sh").read_text()


@pytest.fixture
def gnupg(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A throwaway keyring with a node key and a signing key."""
    # short path: gpg-agent's socket path must stay below ~108 characters
    with tempfile.TemporaryDirectory(prefix="gpg", dir="/tmp") as home:
        monkeypatch.setenv("GNUPGHOME", home)
        for name in ["agq001", "user_key"]:
            subprocess.run(
                ["gpg", "--batch", "--passphrase", "", "--quick-gen-key", name, "default", "default", "never"],
                check=True,
                capture_output=True,
            )
        yield
        subprocess.run(["gpgconf", "--kill", "gpg-agent"], check=False)


def test_write_encrypts_and_signs(gnupg: None, tmp_path: Path) -> None:
    run_sh, sig = submit.write_jobscript(
        make_original_config(), make_original_run(), "hvs.DUMMY-WRAPPED-TOKEN", tmp_path
    )

    text = run_sh.read_text()
    header = "#!/bin/bash\n/usr/bin/decrypt_and_execute <<EOF\n"
    assert text.startswith(header)
    assert text.endswith("-----END PGP MESSAGE-----\nEOF")
    encrypted = text.removeprefix(header).removesuffix("EOF")
    decrypted = subprocess.run(["gpg", "--decrypt"], input=encrypted, capture_output=True, text=True, check=True)
    assert decrypted.stdout == EXPECTED_COMMAND_SH

    subprocess.run(["gpg", "--verify", str(sig), str(run_sh)], check=True, capture_output=True)


def test_write_leaves_no_plaintext(gnupg: None, tmp_path: Path) -> None:
    submit.write_jobscript(make_original_config(), make_original_run(), "hvs.DUMMY-WRAPPED-TOKEN", tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["run.sh", "run.sh.sig"]


# ---------- Slurm ----------


def submit_calls(monkeypatch: pytest.MonkeyPatch, sbatch_out: str) -> tuple[list[list[str]], str]:
    calls: list[list[str]] = []

    def run(cmd: list[str], input: str | None = None, env: dict[str, str] | None = None) -> str:
        calls.append(cmd)
        return sbatch_out if cmd[0] == "ssh" else ""

    monkeypatch.setattr(utils, "run", run)
    job_id = submit.submit_job(make_original_config(), make_original_run(), Path("/j/run.sh"), Path("/j/run.sh.sig"))
    return calls, job_id


def test_submit_job(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, job_id = submit_calls(monkeypatch, "Submitted batch job 4242\n")
    assert job_id == "4242"
    exec_dir = "/mnt/ceph-hdd/cold/u19997/secure"
    sbatch = "/usr/local/slurm/slurm/current/install/bin/sbatch"
    assert calls == [
        ["scp", "/j/run.sh", "/j/run.sh.sig", f"u19997@glogin7.hpc.gwdg.de:{exec_dir}/"],
        [
            "ssh",
            "u19997@glogin7.hpc.gwdg.de",
            shlex.join(
                ["sh", "-c", f"cd {exec_dir} && {sbatch} --reservation=secure-hpc --partition=secure-hpc run.sh"]
            ),
        ],
    ]


def test_submit_job_unexpected_output(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(CommandError, match="unexpected output from sbatch"):
        submit_calls(monkeypatch, "sbatch: error: Batch job submission failed\n")


def wait_calls(monkeypatch: pytest.MonkeyPatch, states: list[str]) -> list[list[str]]:
    """wait_for_job against a fake sacct that answers with `states`, one per poll."""
    calls: list[list[str]] = []
    answers = iter(states)

    def run(cmd: list[str], input: str | None = None, env: dict[str, str] | None = None) -> str:
        calls.append(cmd)
        return next(answers)

    monkeypatch.setattr(utils, "run", run)
    monkeypatch.setattr(submit.time, "sleep", lambda s: None)
    submit.wait_for_job(make_original_config(), make_original_run(), "4242")
    return calls


def test_wait_for_job_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    # empty first: sacct doesn't know the job yet right after submitting
    calls = wait_calls(monkeypatch, ["", "PENDING\n", "RUNNING\n", "RUNNING\n", "COMPLETED\n"])
    assert len(calls) == 5
    sacct = "/usr/local/slurm/slurm/current/install/bin/sacct"
    assert calls[0] == [
        "ssh",
        "u19997@glogin7.hpc.gwdg.de",
        shlex.join([sacct, "-j", "4242", "-X", "--noheader", "--parsable2", "--format=State"]),
    ]


@pytest.mark.parametrize("state", ["FAILED", "CANCELLED by 15733", "TIMEOUT", "OUT_OF_MEMORY"])
def test_wait_for_job_not_completed(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    with pytest.raises(CommandError, match=r"ended as \w+, see its log: .*/slurm-4242\.out"):
        wait_calls(monkeypatch, ["RUNNING\n", f"{state}\n"])


def test_download_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(utils, "run", lambda cmd, input=None, env=None: calls.append(cmd) or "")
    submit.download_image(make_original_config(), make_original_run(), tmp_path)
    assert calls == [
        [
            "scp",
            "u19997@glogin7.hpc.gwdg.de:/mnt/ceph-hdd/cold/u19997/secure/outdata.img",
            str(tmp_path / "outdata.img"),
        ]
    ]
