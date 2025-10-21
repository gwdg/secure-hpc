#!/bin/bash

EXEC_DIR=$1

export VAULT_ADDR='https://kms.hpc.gwdg.de:443'
#token is provided by admin
export VAULT_TOKEN=$( cat secret/user_2.token )


echo "Generating tokens for node.."

default_token=$( vault token create -tls-skip-verify -policy=default -use-limit=1 -field=token )
wrapped_token=$( vault token create -tls-skip-verify -policy=user_2-node -wrap-ttl=3000 \
		       -use-limit=3 -field=wrapping_token )

echo "Tokens"
echo $default_token
echo $wrapped_token

echo "Exec dir:"
echo $EXEC_DIR

cp -f command.sh.template command.sh

sed -i "s/<DEFAULT_TOKEN>/$default_token/g" command.sh
sed -i "s/<WRAPPED_TOKEN>/$wrapped_token/g" command.sh
sed -i "s#<EXEC_DIR>#$EXEC_DIR#g" command.sh

./sendkey.sh data/user_2/outdata @outdata.key
./sendkey.sh data/user_2/rsa_pri @rsa_pri.pem
