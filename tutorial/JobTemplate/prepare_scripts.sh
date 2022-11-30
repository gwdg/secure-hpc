#!/bin/bash

LOCAL_UID=$1
LUKSCONTAINERNAME=$2

export VAULT_ADDR='https://141.5.111.67:81'
#token is provided by admin
export VAULT_TOKEN=$( cat secret/$LOCAL_UID.token )
echo $VAULT_TOKEN
echo "Generating tokens for node.."

default_token=$( vault token create -tls-skip-verify -policy=default -use-limit=1 -field=token )
wrapped_token=$( vault token create -tls-skip-verify -policy=$LOCAL_UID-node -wrap-ttl=3000 \
                       -use-limit=2 -field=wrapping_token )

echo "Tokens"
echo $default_token
echo $wrapped_token

cp command.sh.template command.sh

sed -i "s/<DEFAULT_TOKEN>/$default_token/g" command.sh
sed -i "s/<WRAPPED_TOKEN>/$wrapped_token/g" command.sh

/opt/secure_workflow/sendkey.sh $LOCAL_UID/$LUKSCONTAINERNAME @$LUKSCONTAINERNAME.key
/opt/secure_workflow/sendkey.sh $LOCAL_UID/rsa_pri @rsa_pri.key
