#!/bin/bash

container_name=$1

if ! [[ $container_name =~ ^[a-zA-Z1-9]+$ ]]; then
    echo 'Wrong Container Name. Only a-zA-Z and numbers 1-9 are allowed' >&2
    exit 1
fi

if [[ $EUID -ne 0 ]] ; then
    user_name=$(whoami)
    sudo mount_data $1 $user_name
    exit 0
fi

if [ -z "$2" ]; then
    echo "Please don't execute this script with sudo" >&2
    exit 1
fi

user_name=$2

container_file=/scratch/users/${user_name}/secure/${container_name}.img

cryptsetup luksOpen $container_file $container_name --key-file $key_file

mkdir -p /data/$user_name/$container_name
chmod 711 -R /data
chmod 711 -R /data/$user_name

mount -o rw,noexec,nosuid,nodev  -t ext4 /dev/mapper/$container_name /data/$user_name/$container_name

echo "USER: $user_name"
chown -R $user_name: /data/$user_name/$container_name
chmod 700 -R /data/$user_name/$container_name
ls -l /data/$user_name/$container_name

echo "Data is mounted under /data/$user_name/$container_name"

