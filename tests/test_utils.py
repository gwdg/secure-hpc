import pytest

from securehpc import utils
from securehpc.utils import CommandError


def test_run_returns_stdout() -> None:
    assert utils.run(["echo", "hi there"]) == "hi there\n"


def test_run_passes_input() -> None:
    assert utils.run(["tr", "a-z", "A-Z"], input="secret") == "SECRET"


def test_run_failure_includes_stderr() -> None:
    with pytest.raises(CommandError, match="exit code 3: oops"):
        utils.run(["sh", "-c", "echo oops >&2; exit 3"])


def test_background_stops_process() -> None:
    with utils.background(["sleep", "100"]) as proc:
        assert proc.poll() is None
    assert proc.returncode is not None


def test_background_stops_process_on_exception() -> None:
    with pytest.raises(RuntimeError), utils.background(["sleep", "100"]) as proc:
        raise RuntimeError("boom")
    assert proc.returncode is not None
