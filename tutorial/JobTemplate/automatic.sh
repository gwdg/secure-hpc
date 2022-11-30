#!/bin/bash

LOCAL_UID=$1
HPC_UID=$2
DATA_CONTAINER=$3
PATH_TO_DATA="./data"
PATH_TO_UTILS="/opt/secure_workflow"
PUBKEY_SERVER="agq001"

#umount just to be sure 
$PATH_TO_UTILS/umount_data_container.sh $DATA_CONTAINER /mnt/$LOCAL_UID

### Encrypting the Data with $UID
# Create a LUKS data container using a helper script located

echo "YES" | $PATH_TO_UTILS/create_data_container.sh $DATA_CONTAINER /mnt/$LOCAL_UID 50

# copy the data into the container to encrypt it
cp $PATH_TO_DATA/* /mnt/$LOCAL_UID/$DATA_CONTAINER/

# umount the LUKS data container with a wrapper script used as follows
$PATH_TO_UTILS/umount_data_container.sh $DATA_CONTAINER /mnt/$LOCAL_UID

# Create a directory on the server that will contain the encrypted container
ssh $HPC_UID@gwdu101.gwdg.de 'HPC_UID=$(whoami) && mkdir /scratch/users/$HPC_UID/secure'

# upload your LUKS container into this directory
scp $DATA_CONTAINER.img $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/secure

### Building an Encrypted Singularity/Apptainer Container
# build a Singularity Container, you can use a helper script
./buildEncryptedSingularity.sh

# Since the container is encrypted you can securely upload it in a home dir on the scratch file system
ssh $HPC_UID@gwdu101.gwdg.de 'HPC_UID=$(whoami) && mkdir /scratch/users/$HPC_UID/home'
scp bart_fft_enc.sif $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/home

### Uploading Keys and Writing a Batch Script
# After editing the files command.sh and command.sh.template, 
./prepare_scripts.sh $LOCAL_UID $DATA_CONTAINER

### Enrypting your Batch Script 
# command.sh contain the tokens to retrieve the keys from Vault, thus should be encrypted. It's done using gpg
# a helper script in $PATH_TO_UTILS/encrypt_script.sh which you can call as follows:
# WARNING! You might need to import the public key first
gpg --import /tmp/agqkey
$PATH_TO_UTILS/encrypt_script.sh command.sh $PUBKEY_SERVER

# Passing the gpg message to a decrypt_and_execute function
rm run.sh

echo '#!'"/bin/bash" > run.sh
echo "/usr/bin/decrypt_and_execute <<EOF" >> run.sh
cat command.sh.asc >> run.sh
echo -n "EOF" >> run.sh

cat run.sh

### Signing your Batch Script and Securely Submitting Your Job
# Perform the detached signature, by importing the secret (private) key first 
gpg --import /tmp/user_priv
gpg --detach-sign --local-user user_key -o run.sh.sig run.sh

# Upload run.sh and run.sh.sig to the frontend
scp run.sh run.sh.sig $HPC_UID@gwdu101.gwdg.de:/scratch/users/$HPC_UID/home/

# Submit the job
#ssh $HPC_UID@gwdu101.gwdg.de 'HPC_UID=$(whoami) && cd /scratch/users/$HPC_UID/home ; /opt/slurm/bin/sbatch -p secure --exclusive run.sh'

#submit and check slurm job
slurmid=$(ssh $HPC_UID@gwdu101.gwdg.de 'HPC_UID=$(whoami) && cd /scratch/users/$HPC_UID/home/ ; /opt/slurm/bin/sbatch -p secure -G 1 --time=2-00:00:00 -n 16 --mem=40G run.sh' | gawk '{print $4}')
echo "Printe SlurmID"
echo $slurmid
sleep 5
while [[ $(ssh $HPC_UID@gwdu101.gwdg.de "/opt/slurm/bin/sacct -b -j $slurmid | gawk '{print $2}' | awk 'FNR > 2' | grep -v COMPLETED") != "" ]] ; do echo "Waiting for job to end!" ; sleep 10 ; done
echo 'finished'

sleep 30
$PATH_TO_UTILS/umount_data_container.sh $DATA_CONTAINER /mnt/$LOCAL_UID
# The result should be stored in the same LUKS data container. You can fetch it again via scp
scp $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/secure/$DATA_CONTAINER.img .

# mount the container 
$PATH_TO_UTILS/mount_container.sh $DATA_CONTAINER
