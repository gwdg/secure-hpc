#!/usr/bin/env python3
# Script to encrypt the run script with receiver being slurm
# it is assumed that the user has the slurm recipient on the key ring
# result is a file named $file_name.gpg
import subprocess
import sys


def encrypt_script(file_name: str, recipient: str) -> None:
    subprocess.run(
        ["gpg", "--armor", "--recipient", recipient,
         "--trust-model", "always", "--encrypt", file_name],
        check=True,
    )


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print("Usage: encrypt_script.py <file_name> <recipient>")
        sys.exit(1)
    encrypt_script(sys.argv[1], sys.argv[2])
