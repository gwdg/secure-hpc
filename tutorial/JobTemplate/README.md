# Job Template

Scripts for implementation of Secure HPC on a VM. For description of the scripts refer to [this README](https://gitlab-ce.gwdg.de/sharanya.achut1/secure-hpc/-/blob/master/client/README.md).

### automatic.sh

Usage: ./automatic.sh <ID> <UID_on_HPC> 

Used variables: 
- `UID`: UserID on local
- `HPC-UID`: User ID on the HPC server
- `PATH_TO_DATA`: Path to data folder
- `PATH_TO_UTILS`: Path to directory containing wrapper scripts
- `PUBKEY_SERVER`: Public key of the hpc server for encryption of command.sh
- `PRIVKEY_USER`: Private key of the user for identification on the cluster

