import argparse
import logging
import sys

from securehpc import config, health
from securehpc.config import ConfigError

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Client for running secure workflows on shared HPC systems")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_health = subparsers.add_parser("health", help="Check the setup with a dummy run")
    parser_health.add_argument("--client-only", action="store_true", help="Only check the local machine")
    parser_health.set_defaults(func=lambda args, cfg: health.run(cfg, args.client_only))

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
