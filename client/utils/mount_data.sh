#!/bin/bash

container_name=$1

user=$(whoami)

key_file=${container_name}.key 									# Created when calling create_data_container.sh
container_file=${container_name}.img

sudo cryptsetup luksOpen $container_file $container_name --key-file $key_file			# Encrypt img file in LUKs format with key file
sudo mkdir -p /mnt/$container_name								# Create directory in mount path	

sudo mount -o rw,noexec,nosuid,nodev -t ext4 /dev/mapper/$container_name /mnt/$container_name	# Mount device $container_name (Already created?) to path
sudo chmod 711 -R /mnt/$container_name

sudo chown -R $user /mnt/$container_name
sudo chmod 700 -R /mnt/$container_name
ls -l /mnt/$container_name
