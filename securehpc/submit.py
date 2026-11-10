import logging
import sys
from pathlib import Path

from securehpc import checks, config, utils
from securehpc.config import Config

log = logging.getLogger(__name__)


def run(cfg: Config, run_file: Path, proxy: bool) -> None:
    run_cfg = config.load_run(run_file)

    problems = checks.check_client(cfg) + checks.check_run(run_cfg)
    # TODO: remote checks, once the SSH and Vault steps exist:
    # - SSH to the login node works
    # - the Vault token is valid (through the proxy with --proxy)
    # - exec_dir exists on the cluster and is private (chmod 700)
    # - the container exists in exec_dir
    for problem in problems:
        log.error(problem)
    if problems:
        log.error("%d problem(s) found, nothing was submitted", len(problems))
        sys.exit(1)

    utils.cache_sudo_credentials()
    log.info("submit (proxy=%s) is not implemented yet", proxy)
