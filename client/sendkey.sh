#!/bin/bash
# sends keys to vault, used by user
# if you want to read from a file use @filename
vault kv put secret/$1 key=$2
