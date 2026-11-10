# SecureHPC

## How to run

```bash
uv run securehpc
```

Jobs run one at a time: each `submit` reuses the same files on the cluster, so wait for a job to finish before submitting the next.
