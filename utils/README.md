# utils 
Wrappers for scripts in `../run_workflow`
### create_data_container.sh 
Usage: `create_data_container.sh <container_name> <mount_path> <size>`
- Prepares container (`.img`) file of `<size>` MB
- Creates key `<container_name>.key` for encrypting image file
- Opens LUKS partition and mounts encrypted image file in `<mount_path>`
 
### umount_data_container.sh: 
Usage: `umount_data_container.sh <container_name> <mount_path>` 
- Unmounts data container from specified mount path
- Closes LUKS partition, deletes loop devices created

### mount_data.sh:
Usage: `mount_data.sh <container_name>`
- Encrypts image file with key previously created
- Mounts it in `mount path` 

### encrypt_script.sh
Usage: `encrypt_script.sh <file_name> <recipient>`
- Generates <file_name>.asc with recipient being slurm

