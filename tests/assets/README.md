# Test assets

Expected outputs, generated once by running the original bash client (`old/` at commit `f8df9f7`), so the tests do not depend on `old/` still existing.

- `command.sh`: output of `old/prepare_scripts.sh /mnt/ceph-hdd/cold/u19997/secure`, with a fake `vault` on `PATH` that returns the dummy tokens `hvs.DUMMY-DEFAULT-TOKEN` and `hvs.DUMMY-WRAPPED-TOKEN`.
- `command.sh.asc`: output of `old/utils/encrypt_script.sh command.sh agq001`, encrypted for a throwaway key. Only used as input for wrapping, its content does not matter.
- `run.sh`: output of the `#prepare run.sh` snippet from `old/secure_sbatch`, run on the `command.sh.asc` above.
