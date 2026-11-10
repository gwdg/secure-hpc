import logging

from securehpc import utils
from securehpc.config import Config

log = logging.getLogger(__name__)


def run(cfg: Config) -> None:
    utils.cache_sudo_credentials()
    log.info("submit is not implemented yet")
