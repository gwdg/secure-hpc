#!/bin/bash

# /opt/secure_workflow/deactivate_slurmd.sh

token_setup=hvs.DUMMY-DEFAULT-TOKEN
token=hvs.DUMMY-WRAPPED-TOKEN

exec_dir=/mnt/ceph-hdd/cold/u19997/secure

export VAULT_ADDR='https://kms.hpc.gwdg.de'
VAULT_TOKEN=$token_setup

token=$(vault unwrap -tls-skip-verify -field=token $token)

export VAULT_TOKEN=$token

getkey user_2 outdata
getkey user_2 rsa_pri

echo "Mounting data.."
mount_data outdata $exec_dir

ls /keys/${SLURM_JOB_ID}

# TODO: Do not hard code the username here
/usr/local/bin/singularity exec --nv --pem-path=/keys/${SLURM_JOB_ID}/rsa_pri.key --bind /data/u19997/${SLURM_JOB_ID}/outdata/:/output/ \
		$exec_dir/container.sif bash -c 'echo "In the input file was: \"$(cat /output/input.txt)\"" > /output/output.txt'
ls /data/u19997/${SLURM_JOB_ID}/outdata

echo "UMounting data.."
umount_data outdata

