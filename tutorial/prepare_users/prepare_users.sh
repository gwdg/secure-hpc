#!/bin/bash

NUMBER_OF_USERS=$1
UNAME="user_"

for (( i=1; i<=${NUMBER_OF_USERS}; i++ ))
do
   if id "$UNAME$i" &>/dev/null
   then
	   # If user exists, remove home contents
	   echo "User exists"
	   sudo rm -rf /home/$UNAME$i/*

   else
	   # Creates user with default shell bash
	   sudo useradd -s /usr/bin/bash "$UNAME$i"
	   sudo mkdir /home/$UNAME$i
	   sudo chown $UNAME$i:$UNAME$i /home/$UNAME$i 
           
	   # Generates random 5 digit alphanumeric pwd
   	   PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 5 ; echo '')
	   echo $UNAME$i:$PASS | sudo chpasswd 
           echo "$UNAME$i $PASS" >> user_logins.txt
           
	   # Generate ssh-keypair in user's home dir without pwd
	   sudo mkdir /home/$UNAME$i/.ssh  
	   sudo ssh-keygen -f /home/$UNAME$i/.ssh/id_rsa -N ""
           
	   # Add user to passwordless sudo and sshd_config
	   echo "AllowUsers $UNAME$i" | sudo tee -a /etc/ssh/sshd_config
	   echo "$UNAME$i ALL = (ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
   fi
 
   # Copy job_template into home dir 
   sudo cp -r /home/cloud/job_template /home/"$UNAME$i"/
   
   # Distribute tokens from vault 
   sudo chmod 777 /home/$UNAME$i/job_template/secret/
   scp cloud@141.5.111.67:/home/cloud/vault/$UNAME$i.token /home/$UNAME$i/job_template/secret 

   # import gpg keys: public key of secure HPC server
   # public-private keypair for detached signature 
   # gpg --import /tmp/agqkey
   # gpg --import /tmp/user_priv

   sudo chown -R $UNAME$i:$UNAME$i /home/$UNAME$i

done

# Reload ssh sevice after changes to sshd_config
sudo service ssh reload

exit
