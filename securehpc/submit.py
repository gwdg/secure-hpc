import logging
import sys
from pathlib import Path

from securehpc import checks, config, debug, utils
from securehpc.config import Config

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
        debug.run_all(cfg, run_cfg)

    utils.cache_sudo_credentials()
    log.info("submit (proxy=%s) is not implemented yet", proxy)
