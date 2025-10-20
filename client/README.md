TODO write how to use (or just reference to the hpc docs)

Files that have to be added to work
- The server key: `agq001.key`
- The user owned keypair for the container encryption: `rsa_pri.pem`, `rsa_pub.pem`
- The vault token given by us `secret/user_2.token`

Also todos
- [ ] `command.sh.template`: dont hardcode the bindmount location; get from `secure_sbatch`
- [ ] `secure_sbatch`: Don't hardcode node names (see `encrypt_script.sh`)
- [ ] `secure_sbatch`: Don't hardcode reservation name (see `encrypt_script.sh`)
- [ ] `prepare_scripts.sh` and `command.sh.template`: Don't hardcode `user_2`
  - TODO Or is `user_2` just a misnamed policy name and it can stay the same between users?
