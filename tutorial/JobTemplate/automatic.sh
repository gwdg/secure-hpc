#!/bin/bash

UID=$1
HPC_UID=$2 
PATH_TO_DATA="./data/"
PATH_TO_UTILS="/opt/secure_workflow"
PUBKEY_SERVER="agq001"
PRIVKEY_USER="user_key" 

# Prepare input data container
echo "YES" | $PATH_TO_UTILS/create_data_container.sh inputdata /mnt/$UID 50
cp $PATH_TO_DATA/* /mnt/$UID/inputdata/
# Verifies data has been copied
ls /mnt/inputdata/
# Unmounts input data container
$PATH_TO_UTILS/umount_data_container.sh inputdata /mnt/$UID
# Copies inputdata.img onto hpc server
scp inputdata.img $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/secure

# Prepare output container
echo "YES" | ../$PATH_TO_UTILS/create_data_container.sh outdata /mnt 500
# Unmounts
$PATH_TO_UTILS/umount_data_container.sh outdata /mnt
# Create a directory on the server
ssh $HPC_UID@gwdu101.gwdg.de 'mkdir /scratch/users/$HPC_UID/secure'
# Copies outdata.img onto hpc server
scp outdata.img $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/secure

# Prepares command.sh, copies generated default and wrapped tokens into it
# Sends keys to vaults
./prepare_scripts.sh

# Creates command.sh.asc, recipient is slurm 
$PATH_TO_UTILS/encrypt_script.sh command.sh $PUBKEY_SERVER 

cat command.sh.asc

# Removes preexisting run.sh
rm run.sh

# Prepares run.sh file 
echo "#!/bin/bash" > run.sh
echo "/usr/bin/decrypt_and_execute <<EOF" >> run.sh
cat command.sh.asc >> run.sh
echo -n "EOF" >> run.sh

cat run.sh

# Creates detached signature for run.sh
gpg --detach-sign --local-user $PRIVKEY_USER -o run.sh.sig run.sh

# Secure copies run.sh, run.sh.sig onto scratch 
scp run.sh run.sh.sig $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/home/

# Executes run.sh on secure client
slurmid=$(ssh <hpc-uid>@gwdu101.gwdg.de 'cd /scratch/users/HPC_UID/home/ ; /opt/slurm/bin/sbatch -p secure -G 1 --time=2-00:00:00 -n 16 --mem=40G run.sh' | gawk '{print $4}')

while [[ $(ssh $HPC_UID@gwdu101.gwdg.de "/opt/slurm/bin/sacct -b -j $slurmid | gawk '{print $2}' | awk 'FNR > 2' | grep -v COMPLETED") != "" ]] ; do echo "Waiting for job to end!" ; sleep 10 ; done

echo 'finished'

# Copies image file from server to local 
scp $HPC_UID@transfer-scc.gwdg.de:/scratch/users/$HPC_UID/secure/outdata.img .

# Mounts outdata
$PATH_TO_UTILS/mount_data.sh outdata
