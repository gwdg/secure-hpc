# SecureHPC

## How to run

```bash
uv run securehpc submit path/to/run.toml
```

On first start, a default config is created at `~/.config/securehpc/config.toml`. Edit it before submitting.

If your machine can't reach Vault directly (for example a VM outside the GWDG network), add `--proxy`: Vault is then reached through an SSH tunnel via the login node. `--debug` runs slower checks of everything first, including Vault.

A job is described by a `run.toml`. Relative paths are relative to the `run.toml` itself:

```toml
exec_dir = "/mnt/ceph-hdd/cold/uXXXXX/secure"  # private folder on the cluster (chmod 700)
container = "./container.sif"                  # local encrypted container, uploaded when it changed
data = "./data"                                # copied into the encrypted image
image_size_mb = 100                            # must fit the input data and the results
command = """
echo "In the input file was: $(cat /output/input.txt)" > /output/output.txt
"""
```

The container must be built encrypted (`apptainer build --pem-path=rsa_pub.pem ...`); `submit` refuses to upload an unencrypted one. On every submit it compares the container's sha256 with `exec_dir/container.sif` on the cluster and uploads it if they differ.

Each submit writes `outdata.img` (the encrypted image), `outdata.key` (its key), `run.sh` and `run.sh.sig` next to the `run.toml`, overwriting the previous ones. Note that the LUKS2 header takes 16 MB of `image_size_mb`.

The command runs inside the container with `bash -c`. The encrypted image is mounted at `/output` and holds both the input data and the results, so read from and write to `/output`.

Jobs run one at a time: each `submit` reuses the same files on the cluster, so wait for a job to finish before submitting the next.

## Key and Token Writeup
There are 5 keys and 2 tokens in general

### Keys
1. Your SSH key: Used for data transfer and submission
2. `outdata.key`: LUKS Passphrase used for `outdata.img`, fetched from vault via Wrapping token
3. Container Key pair (RSA): Public key used to encrypt container.sif on your machine. Private half fetched from vault via Wrapping Token
4. Node GPG Key: Public key to encrypt command.sh (in run.sh), private key to decrypt.
5. User GPG Key: Private half to sign run.sh (as run.sh.sig), public half for node to check sig

Furthermore, in the old version, there was a single use, default-policy Vault key, but that one was never used.

### Tokens
6. Perma Vault token: To store the LUKS key and Singularity private key in Vault, and to create wrapping tokens per job
7. Wrapping token: Embedded (encrypted by node public key) into command.sh, three uses:
  - Vault unwrap to get the unwrapped token
  - Unwrapped Token: Fetch the LUKS key with it
  - Unwrapped token: Fetch the singularity private key with it

