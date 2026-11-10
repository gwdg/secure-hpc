import argparse
import logging
import sys
from pathlib import Path

from securehpc import config, submit
from securehpc.config import ConfigError
from securehpc.shell import CommandError

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Client for running secure workflows on shared HPC systems")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_submit = subparsers.add_parser("submit", help="Run a job on the secure node")
    parser_submit.add_argument("run_file", type=Path, help="Path to the run.toml describing the job")
    parser_submit.add_argument(
        "--proxy", action="store_true", help="Reach Vault through a SOCKS proxy via the login node"
    )
    parser_submit.set_defaults(func=lambda args, cfg: submit.run(cfg, args.run_file, args.proxy))

    args = parser.parse_args()

    config.ensure_config()
    try:
        cfg = config.load_config()
    except ConfigError as e:
        log.error("Invalid config: %s", e)
        sys.exit(1)
    try:
        args.func(args, cfg)
    except (ConfigError, CommandError) as e:
        log.error("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
