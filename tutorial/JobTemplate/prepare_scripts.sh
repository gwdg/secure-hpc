#!/bin/bash

export VAULT_ADDR='https://141.5.111.67:81'
#token is provided by admin
export VAULT_TOKEN=$( cat secret/<uid>.token )

echo "Generating tokens for node.."

default_token=$( vault token create -tls-skip-verify -policy=default -use-limit=1 -field=token )
wrapped_token=$( vault token create -tls-skip-verify -policy=<uid>-node -wrap-ttl=3000 \
		       -use-limit=3 -field=wrapping_token )

echo "Tokens"
echo $default_token
echo $wrapped_token

cp command.sh.template command.sh

sed -i "s/<DEFAULT_TOKEN>/$default_token/g" command.sh
sed -i "s/<WRAPPED_TOKEN>/$wrapped_token/g" command.sh

/opt/secure_workflow/sendkey.sh <uid>/<LUKScontainername> @<LUKScontainername>.key
/opt/secure_workflow/sendkey.sh <uid>/rsa_pri @rsa_pri.key
