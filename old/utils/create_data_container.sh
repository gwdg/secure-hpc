#!/bin/bash
if [ "$1" == "-h" -o "$1" == "--help" ]; then
    echo "Program used t create a data container. Usage: create_data_container.sh <container_name> <mount_path> <size> .  Here, <mount_path> is the mount path on your local system where the container will be mounted. <size> expects the size of the data container in MB to the base of 10. "
    exit 0
fi
container_name=$1
container_file=${container_name}.img
key_file=${container_name}.key
mount_path=$2
size=$3
if ! [[ $container_name =~ ^[a-zA-Z1-9]+$ ]]; then
    echo 'Wrong Container Name. Only a-zA-Z and numbers 1-9 are allowed' >&2
    exit 1
fi
username=$(whoami)
loop_dev=$(sudo losetup -f )
dd if=/dev/zero of=$container_file bs=1M count=$size
tr -dc '0-9a-zA-Z' </dev/urandom | head -c 32 > $key_file
sudo losetup $loop_dev $container_file
sudo cryptsetup -c aes-xts-plain -s 512 luksFormat $loop_dev $key_file
sudo cryptsetup luksOpen $loop_dev $container_name --key-file $key_file
sudo mkfs.ext4 /dev/mapper/$container_name
sudo mkdir -p $mount_path/$container_name
sudo mount -t ext4 /dev/mapper/$container_name $mount_path/$container_name
sudo chown -R $username $mount_path/$container_name
