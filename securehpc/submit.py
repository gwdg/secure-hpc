import logging

from securehpc import utils
from securehpc.config import Config

log = logging.getLogger(__name__)


def run(cfg: Config, proxy: bool) -> None:
    utils.cache_sudo_credentials()
    log.info("submit (proxy=%s) is not implemented yet", proxy)
