import importlib.resources
import tomllib
from pathlib import Path

import pytest

from securehpc import checks, utils
from securehpc.config import Config, RunConfig

DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()

SCONTROL_OUT = """\
ReservationName=secure-hpc-example StartTime=2026-01-01T00:00:00 EndTime=2027-01-01T00:00:00 Duration=365-00:00:00
   Nodes=node001 NodeCnt=1 CoreCnt=32 Features=(null) PartitionName=(null) Flags=SPEC_NODES,STATIC
   TRES=cpu=32
   AllowedPartitions=(null) QOS=(null)
   Users=u00001,u00002,u00003 Groups=(null) Accounts=(null) Licenses=(null) State=ACTIVE BurstBuffer=(null)
   MaxStartDelay=(null)
"""


SIF_LIST_ENCRYPTED = """\
------------------------------------------------------------------------------
ID   |GROUP   |LINK    |SIF POSITION (start-end)  |TYPE
------------------------------------------------------------------------------
1    |1       |NONE    |32176-32208               |Def.FILE
2    |1       |NONE    |32208-34400               |JSON.Generic
3    |1       |NONE    |34400-34912               |Cryptographic Message (PEM/RSA-OAEP)
4    |1       |NONE    |36864-31932416            |FS (Encrypted squashfs/*System/amd64)
"""
SIF_LIST_PLAIN = SIF_LIST_ENCRYPTED.replace("FS (Encrypted squashfs", "FS (Squashfs")


def make_config(text: str = DEFAULT_TEXT) -> Config:
    return Config.from_dict(tomllib.loads(text))


def make_run(tmp_path: Path, **overrides: object) -> RunConfig:
    d = {
        "exec_dir": "/mnt/ceph-hdd/cold/u12345/secure",
        "container": "container.sif",
        "data": ".",
        "image_size_mb": 100,
        "command": "echo hi",
    }
    return RunConfig.from_dict(d | overrides, tmp_path)


def test_placeholders_reported() -> None:
    assert len(checks.check_placeholders(make_config())) == 1


def test_placeholders_replaced() -> None:
    assert checks.check_placeholders(make_config(DEFAULT_TEXT.replace("uXXXXX", "u12345"))) == []


def test_run_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "container.sif").write_text("x")
    monkeypatch.setattr(utils, "run", lambda cmd, input=None: SIF_LIST_ENCRYPTED)
    assert checks.check_run(make_run(tmp_path)) == []


def test_run_problems(tmp_path: Path) -> None:
    run_cfg = make_run(tmp_path, exec_dir="/x/uXXXXX/secure", data="nope", command="  \n", container="nope.sif")
    assert len(checks.check_run(run_cfg)) == 4


@pytest.mark.parametrize(
    ("sif_list", "encrypted"),
    [
        (SIF_LIST_ENCRYPTED, True),
        (SIF_LIST_PLAIN, False),
        (SIF_LIST_ENCRYPTED + SIF_LIST_PLAIN.splitlines()[-1], False),  # one plain partition is enough to refuse
        ("", False),  # no filesystem at all: refuse rather than guess
    ],
)
def test_container_encrypted(monkeypatch: pytest.MonkeyPatch, sif_list: str, encrypted: bool) -> None:
    monkeypatch.setattr(utils, "run", lambda cmd, input=None: sif_list)
    assert (checks.check_container_encrypted(Path("c.sif")) == []) == encrypted


def test_secret_file_missing(tmp_path: Path) -> None:
    assert checks.check_secret_file(tmp_path / "nope") == [f"File not found: {tmp_path / 'nope'}"]


def test_secret_file_readable_by_others(tmp_path: Path) -> None:
    path = tmp_path / "token"
    path.write_text("x")
    path.chmod(0o644)
    assert "chmod 600" in checks.check_secret_file(path)[0]


def test_secret_file_private(tmp_path: Path) -> None:
    path = tmp_path / "token"
    path.write_text("x")
    path.chmod(0o600)
    assert checks.check_secret_file(path) == []


def test_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks, "CLIENT_TOOLS", ["sh", "securehpc-no-such-tool"])
    assert checks.check_tools() == ["Tool not found in PATH: securehpc-no-such-tool"]


def test_path_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PATH")
    assert checks.check_client(make_config()) == ["PATH is not set"]


# ---------- debug checks ----------


def test_parse_scontrol() -> None:
    fields = checks.parse_scontrol(SCONTROL_OUT)
    assert fields["ReservationName"] == "secure-hpc-example"
    assert fields["State"] == "ACTIVE"
    assert fields["Users"] == "u00001,u00002,u00003"
    assert fields["TRES"] == "cpu=32"  # only split at the first "="


def test_data_fits(tmp_path: Path) -> None:
    (tmp_path / "data" / "sub").mkdir(parents=True)
    (tmp_path / "data" / "sub" / "a.bin").write_bytes(b"x" * 2**20)
    checks.data_fits(make_config(), make_run(tmp_path, data="data", image_size_mb=2))
    with pytest.raises(RuntimeError, match="image_size_mb is 1"):
        checks.data_fits(make_config(), make_run(tmp_path, data="data", image_size_mb=1))


def test_data_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not found"):
        checks.data_fits(make_config(), make_run(tmp_path, data="data", image_size_mb=1))
