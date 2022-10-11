echo "=== JOB ===" >> $LOG
echo $SLURM_JOB_ID >> $LOG
echo $SLURM_JOB_WORK_DIR >> $LOG

# Of course, very bad practise. I know :(
file_name=$(scontrol show job $SLURM_JOB_ID | grep "Command" | tr '=' ' ' | awk '{print $2}' )
echo $file_name >> $LOG

function check_file_signature() {

    name=$1
    signature="$name".sig
    if ! gpg --verify $signature $name; then
	#bad -> abort execution
	echo "Wrong signature!" >> $LOG
	# when exit code is not 0, the node will drain!!!
	scancel $SLURM_JOB_ID
	exit 1 
    fi 
}

check_file_signature $file_name

if cmp $file_name /var/spool/slurm/d/job$SLURM_JOB_ID/slurm_script; then
  echo "Batch Scipte sind nicht gleich" >> $LOG
  scancel $SLURM_JOB_ID
  exit 1
fi

echo "=================" >> $LOG

