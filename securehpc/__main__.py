import argparse
import logging
import sys

from securehpc import config
from securehpc.config import Config, ConfigError

log = logging.getLogger(__name__)


def health(cfg: Config, client_only: bool) -> None:
    # TODO: dummy run; with client_only, skip everything that needs the cluster
    log.info("health check (client_only=%s) not implemented yet", client_only)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Client for running secure workflows on shared HPC systems")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_health = subparsers.add_parser("health", help="Check the setup with a dummy run")
    parser_health.add_argument("--client-only", action="store_true", help="Only check the local machine")
    parser_health.set_defaults(func=lambda args, cfg: health(cfg, args.client_only))

    args = parser.parse_args()

    config.ensure_config()
    try:
        cfg = config.load_config()
    except ConfigError as e:
        log.error("Invalid config: %s", e)
        sys.exit(1)
    args.func(args, cfg)


if __name__ == "__main__":
    main()
