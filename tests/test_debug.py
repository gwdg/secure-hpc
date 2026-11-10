import importlib.resources
import tomllib
from pathlib import Path

import pytest

from securehpc import debug
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


def make_run(tmp_path: Path, image_size_mb: int) -> RunConfig:
    d = {"exec_dir": "/x", "container": "c.sif", "data": "data", "image_size_mb": image_size_mb, "command": "true"}
    return RunConfig.from_dict(d, tmp_path)


def test_parse_scontrol() -> None:
    fields = debug.parse_scontrol(SCONTROL_OUT)
    assert fields["ReservationName"] == "secure-hpc-example"
    assert fields["State"] == "ACTIVE"
    assert fields["Users"] == "u00001,u00002,u00003"
    assert fields["TRES"] == "cpu=32"  # only split at the first "="


def test_data_fits(tmp_path: Path) -> None:
    (tmp_path / "data" / "sub").mkdir(parents=True)
    (tmp_path / "data" / "sub" / "a.bin").write_bytes(b"x" * 2**20)
    cfg = Config.from_dict(tomllib.loads(DEFAULT_TEXT))
    debug.data_fits(cfg, make_run(tmp_path, 2))
    with pytest.raises(RuntimeError, match="image_size_mb is 1"):
        debug.data_fits(cfg, make_run(tmp_path, 1))


def test_data_missing(tmp_path: Path) -> None:
    cfg = Config.from_dict(tomllib.loads(DEFAULT_TEXT))
    with pytest.raises(RuntimeError, match="not found"):
        debug.data_fits(cfg, make_run(tmp_path, 1))
