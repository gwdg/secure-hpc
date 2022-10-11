#!/bin/bash
# the one executing this script need to have the slurm private key

set -e

# erster call ist mit EOF file ohne sudo

if [[ $EUID -ne 0 ]] ; then
    user_name=$(whoami)
    file_name="run.sh.asc"
    cat $1 > /keys/$file_name
    sudo decrypt_and_execute $file_name $user_name
    exit 0
fi

if [ -z "$2" ]; then
    echo "Please don't execute this script with sudo" >&2
    exit 1
fi

file_name=$1
user_name=$2

echo "Decrypting.."
gpg --no-tty --output /keys/run.sh --decrypt /keys/run.sh.asc

#remove signed script and encrypted
rm /keys/run.sh.asc

chown $user_name: /keys/run.sh

sudo -u $user_name chmod +x /keys/run.sh

# trouble running the script resulted in the next line
#sudo -u $user_name dos2unix -k -o /keys/run.sh

echo "Changing directory"
cd /usr/users/$user_name
echo "Running script"
sudo -u $user_name /keys/run.sh

echo "Clean up"

# remove everything in /keys, the standard should be, that every user has clean directory
sudo rm -f /keys/*
