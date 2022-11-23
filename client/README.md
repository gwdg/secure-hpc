# run_workflow

### automatic.sh
Used variables: `uid`, `hpc-uid`, `pubKeyOfServer`, `LocalUserKey`, `hpc-frontend`
- End-to-end automation of the secure workflow
- Prepares input and output data containers, keys
- Prepare command.sh to be executed on the secure hpc server (as `run.sh`) 
- Creates detached signature, copies `run.sh` and `run.sh.sig` onto scratch/home and executes `run.sh` 
- Copies output image file to local and mounts for use

### prepare_scripts.sh
Usage: `prepare_scripts.sh`
- Creates default and wrapped tokens and copies into `command.sh`
- Sends keys for inputdata, outdata and rsi_private to the vault 

### sendkey.sh
Usage: `sendkey.sh <path> @<key_file>`
- Sends key file to the vault 

### command.sh
- Encrypted with `encrpt_script.sh` and copied into `run.sh`
- Contains singularity call

### command.sh.template
- Template file for `command.sh`, contains placeholders for tokens
