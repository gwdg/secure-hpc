# SecureHPC

## How to run

```bash
uv run securehpc submit path/to/run.toml
```

On first start, a default config is created at `~/.config/securehpc/config.toml`. Edit it before submitting.

A job is described by a `run.toml`. Relative paths are relative to the `run.toml` itself:

```toml
exec_dir = "/mnt/ceph-hdd/cold/uXXXXX/secure"  # private folder on the cluster (chmod 700)
container = "container.sif"                    # encrypted container, already uploaded to exec_dir
data = "./data"                                # copied into the encrypted image
image_size_mb = 100                            # must fit the input data and the results
command = """
echo "In the input file was: $(cat /output/input.txt)" > /output/output.txt
"""
```

The command runs inside the container with `bash -c`. The encrypted image is mounted at `/output` and holds both the input data and the results, so read from and write to `/output`.

Jobs run one at a time: each `submit` reuses the same files on the cluster, so wait for a job to finish before submitting the next.
