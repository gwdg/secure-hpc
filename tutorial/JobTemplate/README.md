# Job Template

Scripts for implementation of Secure HPC on a VM. For description of the scripts refer to [this README](https://gitlab-ce.gwdg.de/sharanya.achut1/secure-hpc/-/blob/master/client/README.md).

### automatic.sh

Usage: `./automatic.sh <local-uid> <hpc_uid> <LUKScontainername>` 

Used variables: 
- `LOCAL_UID`: UserID on local
- `HPC-UID`: User ID on the HPC server
- `DATA_CONTAINER`: Your chosen name for the LUKS container
- `PATH_TO_DATA`: Path to data folder
- `PATH_TO_UTILS`: Path to directory containing wrapper scripts
- `PUBKEY_SERVER`: Public key of the hpc server for encryption of command.sh

### prepare_scripts

Usage: `./prepare_scripts.sh <local-uid> <LUKScontainername>`
