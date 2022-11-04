#!/bin/bash

export VAULT_ADDR=''
# Token is provided by admin
export VAULT_TOKEN=$( cat secret/user_2.token )

echo "Generating tokens for node.."

# Create default token with vault with default policy
default_token=$( vault token create -policy=default -use-limit=1 -field=token )
# Create wrapping token for time 3000, with use limit 3
wrapped_token=$( vault token create -policy=user_2-node -wrap-ttl=3000 \
		       -use-limit=3 -field=wrapping_token )

echo "Tokens"
echo $default_token
echo $wrapped_token

# Copy template into command.sh
cp command.sh.template command.sh

# Replace placeholders with generated  default and wrapped tokens in command.sh
sed -i "s/<DEFAULT_TOKEN>/$default_token/g" command.sh
sed -i "s/<WRAPPED_TOKEN>/$wrapped_token/g" command.sh

# Send keys to vault 
# Assumes Vault User is named user_2, see above in secret
./sendkey.sh user_2/inputdata @inputdata.key
./sendkey.sh user_2/outdata @outdata.key
./sendkey.sh user_2/rsa_pri @rsa_pri.key
