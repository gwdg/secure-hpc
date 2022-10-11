#get key is mostly called by node
user=$1
key_name=$2
hpc_uid=$3
vault kv get -field='key' secret/$user/$key_name > /keys/${key_name}.key
