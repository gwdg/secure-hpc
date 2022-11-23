#!/bin/bash

mkdir -p ./build

echo 'Singularity keys'

ssh-keygen -t rsa -b 4096 -m pem -N "" -f ./rsa
ssh-keygen -f ./rsa.pub -e -m pem > rsa_pub.pem
rm rsa.pub
mv rsa rsa_pri.key

echo 'Singularity Build'
sudo singularity build --pem-path=rsa_pub.pem bart_fft_enc.sif ./src/bart_fft.def

echo 'Checking Singularity Image'
if !  [[ $(sudo singularity run  --pem-path=./rsa_pri.key bart_fft_enc.sif bash -c "echo Hello" | grep Hello) ]]; then
    echo "Building the Container didn't work."
    exit 1 ;
fi

