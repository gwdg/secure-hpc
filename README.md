# Secure Workflow HPC

![securehpc](https://pad.gwdg.de/uploads/5807c926-caf1-4381-96bc-647daa073187.png)<!--(./secure_submission_neu.png)-->

A secure workflow for the transfer, storing and processing of sensitive data. This is an implementation of ["A Secure Workflow for Shared HPC Systems"](https://ieeexplore.ieee.org/abstract/document/9826008/references#references) at [GWDG](https://gwdg.de/). 

## Note on the Server

Due to changes in our server image infrastructure, it is not trivial to easily version the server files to this git repository. Thus, for now, this repository only contains the client files needed to create and submit SecureHPC SLURM jobs.

For the last public version containing the server code, see the `serverclient` branch, or the according git tag or github release.

If you or your institution has interest in running a more recent verison of SecureHPC, feel free to contact [hpc-support@gwdg.de](mailto:hpc-support@gwdg.de).

## Overview
This SecureHPC environment enables the processing of sensitive data such as sensitive medical data on shared HPC Systems. 
    
In a typical user workflow, the user logs in to the frontend and uploads sensitive data. A batch script for processing the data on the compute nodes is run if the user is authorised with a valid `UID`. The processed data is then to be transferred back. This workflow is problematic since it is vulnerable to attacks at several places (for example, if an attacker gains root privileges at the user-end) . The secure workflow ensures security by encrypting data, securing job dependencies in encrypted containers, and using encrypting batch script. Furthermore, a separate Key Server is used for managing keys required for de/encryption. 

## Folders

In this git repo we have
* Client: Client-side files. Creation of data containers and keys, encryption of the batch script and exeution(?) on hpc server.
* Server: Decryption of data and batch file, execution of the batch script, prepating output data container.
* Tutorial: A tutorial for training users in the SecureHPC workflow. Contains `JobTemplate/` with scripts for implementing client-side secure workflow on a VM. 

### Brief description of the secure workflow
- A user with `UID` logs into the front end and uploads a [LUKS]() [1] data container. 
- The batch script is encrpyted and uploaded. Keys are uploaded to the key management server managed by [`Vault`]()<sup>[2]</sup>.
- Identity on the (?) server is verified via an access token. The batch script is decrypted and run on the hpc cluster. Jobs are managed by [Slurm]()<sup>[3]</sup>.
- Output data is mounted for use. (To mention mounting/unmounting of data container and file system? Is there decryption again of the outdata?) 
<!--
It is assumed that the local system of the user and the image server are secure. -->

