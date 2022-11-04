# run_workflow

### automatic.sh
- Driver script
- Prepares input and output data container, copies onto scratch/secure
- Also creates corresponding keys (`.key`)
- Calls prepare_scripts to prepare command.sh
- Encrypts command.sh and copies into run.sh  
- Creates detached signature for run.sh, copies both onto scratch/home 
- Executes run.sh on secure hpc 
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
