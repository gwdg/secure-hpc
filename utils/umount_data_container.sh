#!/bin/bash
container_name=$1
mount_path=$2

sudo umount $mount_path/$container_name
sudo cryptsetup luksClose $container_name

tmp=$(sudo losetup -a | grep "$container_name" | awk '{print $1}')
for elem in $tmp ; do 
    echo "${elem%?}"
    sudo losetup -d "${elem%?}" ;
done

