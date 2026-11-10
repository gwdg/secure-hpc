import importlib.resources
import shlex
import subprocess
import tempfile
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

from securehpc import jobscript
from securehpc.config import Config, RunConfig

ASSETS = Path(__file__).parent / "assets"
DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()

# the values the original client had hardcoded or was called with when the assets were generated
ORIGINAL_COMMAND = 'echo "In the input file was: \\"$(cat /output/input.txt)\\"" > /output/output.txt'


def make_config() -> Config:
    return Config.from_dict(tomllib.loads(DEFAULT_TEXT.replace("uXXXXX", "u19997")))


def make_run(command: str = ORIGINAL_COMMAND) -> RunConfig:
    d = {
        "exec_dir": "/mnt/ceph-hdd/cold/u19997/secure",
        "container": "container.sif",
        "data": ".",
        "image_size_mb": 100,
        "command": command,
    }
    return RunConfig.from_dict(d, Path("."))


def render(command: str = ORIGINAL_COMMAND) -> str:
    return jobscript.render(make_config(), make_run(command), "hvs.DUMMY-DEFAULT-TOKEN", "hvs.DUMMY-WRAPPED-TOKEN")


def test_render_matches_original() -> None:
    assert render() == (ASSETS / "command.sh").read_text()


def test_render_ignores_surrounding_newlines() -> None:
    # a TOML multi-line string ends with a newline
    assert render(f"\n{ORIGINAL_COMMAND}\n") == (ASSETS / "command.sh").read_text()


@pytest.mark.parametrize("command", ["echo 'single quotes'", 'a && b; echo "$HOME" | tr a b', "line1\nline2"])
def test_render_command_survives_quoting(command: str) -> None:
    # the first shell word after "bash -c" must be exactly the command
    after_bash_c = render(command).split("bash -c ", 1)[1]
    assert shlex.split(after_bash_c)[0] == command


def test_wrap_matches_original() -> None:
    assert jobscript.wrap((ASSETS / "command.sh.asc").read_text()) == (ASSETS / "run.sh").read_text()


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
    run_sh, sig = jobscript.write(
        make_config(), make_run(), "hvs.DUMMY-DEFAULT-TOKEN", "hvs.DUMMY-WRAPPED-TOKEN", tmp_path
    )

    text = run_sh.read_text()
    header = "#!/bin/bash\n/usr/bin/decrypt_and_execute <<EOF\n"
    assert text.startswith(header)
    assert text.endswith("-----END PGP MESSAGE-----\nEOF")
    encrypted = text.removeprefix(header).removesuffix("EOF")
    decrypted = subprocess.run(["gpg", "--decrypt"], input=encrypted, capture_output=True, text=True, check=True)
    assert decrypted.stdout == (ASSETS / "command.sh").read_text()

    subprocess.run(["gpg", "--verify", str(sig), str(run_sh)], check=True, capture_output=True)


def test_write_leaves_no_plaintext(gnupg: None, tmp_path: Path) -> None:
    jobscript.write(make_config(), make_run(), "hvs.DUMMY-DEFAULT-TOKEN", "hvs.DUMMY-WRAPPED-TOKEN", tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["run.sh", "run.sh.sig"]
