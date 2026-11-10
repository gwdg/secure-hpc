import logging

from securehpc import shell

log = logging.getLogger(__name__)


def cache_sudo_credentials() -> None:
    """Ask for the sudo password now, so later `sudo` calls don't stop the run to prompt.

    sudo remembers the password for a while (15 minutes by default). Only the commands
    that need root (cryptsetup, losetup, mount) use sudo; everything else runs as the user.
    """
    log.info("Some steps need root (LUKS image, mounting). Asking for your sudo password now.")
    shell.run(["sudo", "-v"])
