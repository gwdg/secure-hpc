# prepare_users.sh
User login set-up on a VM with permissions, and wrapper scripts, data, keys, etc, in ../JobTemplate.

Usage: `./prepare_users.sh <uid_prefix> <number_of_users>`

For example, `./prepare_users.sh user_ 10` creates 10 users, `user_1, ..., user_10`. 

- Outputs `user_logins.txt` with user IDs and passwords of created users. 
- An assumption is that the user IDs and Vault IDs are named alike. If this is not the case, please change the user IDs accordingly when copying tokens from Vault server.  
- You will need to ensure ssh access to the Vault server. It also helps to ensure you have the correct path to the `JobTemplate` directory in case it resides elsewhere (here, it is in the parent directory). 
