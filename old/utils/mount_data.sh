#!/bin/bash

container_name=$1

user=$(whoami)

key_file=${container_name}.key
key_file=$(realpath $key_file)
container_file=${container_name}.img

if ! [ -z ${LOCAL_TMPDIR+x} ]; then
    cp $container_file $LOCAL_TMPDIR
    cd $LOCAL_TMPDIR
elif ! [ -z ${TMP+x} ]; then
    cp $container_file $TMP
    cd $TMP
else 
    cp $container_file /tmp/
    cd /tmp
fi

echo $key_file

sudo cryptsetup luksOpen $container_file $container_name --key-file $key_file
sudo mkdir -p /mnt/$container_name

sudo mount -o rw,noexec,nosuid,nodev -t ext4 /dev/mapper/$container_name /mnt/$container_name
sudo chmod 711 -R /mnt/$container_name

sudo chown -R $user /mnt/$container_name
sudo chmod 700 -R /mnt/$container_name
ls -l /mnt/$container_name
