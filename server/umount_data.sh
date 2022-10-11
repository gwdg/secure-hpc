#!/bin/bash 
container_file=$1
if [[ $EUID -ne 0 ]] ; then
    user_name=$(whoami)
    sudo /usr/bin/umount_data $1 $user_name
    exit 0
fi
user_name=$2
umount /data/"$user_name"/"$container_file"
cryptsetup luksClose "$container_file"
tmp=$(sudo losetup -a | grep "/${container_file}.img" | awk '{print $1}')
for elem in $tmp ; do 
    echo "${elem%?}"
    losetup -d "${elem%?}" ;
done
rm -f /keys/${container_file}.key
echo "Container has been umounted."

