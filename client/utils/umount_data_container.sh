#!/bin/bash

container_name=$1
mount_path=$2

sudo umount $mount_path/$container_name					# Unmount device
sudo cryptsetup luksClose $container_name				# Close LUKS partition "container_name"

tmp=$(sudo losetup -a | grep "$container_name" | awk '{print $1}')	# Grep loop devices with "container_name", filter path 
for elem in $tmp ; do 							# Delete those loop devices
    echo "${elem%?}"
    sudo losetup -d "${elem%?}" ;
done
