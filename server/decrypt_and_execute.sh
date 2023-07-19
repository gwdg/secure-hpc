#!/bin/bash
# root (entered via sudo) needs to have the slurm private key

# First call is without sudo and without arguments
if [[ $EUID -ne 0 ]] ; then
    if [[ $# -ne 0 ]]; then
        echo "Usage: $0 <<EOF"
        echo "<your encrypted script>"
        echo "EOF"
        exit 1
    fi
    user_name=$(whoami)
    script=$(mktemp --tmpdir=/keys)
    cat > "$script"
    if sudo "$0" "$script" "$user_name"; then
        echo "Running script"
        "$script"
    fi
    res=$?

    echo "Clean up"
    rm -f /keys/*

    exit $res
elif [[ $# -eq 0 ]]; then
    echo "Please don't execute this script with sudo" >&2
    exit 1
fi

encrypted_script=${1:?Missing encrypted file}
user_name=${2:?Missing user}
decrypted_script="${encrypted_script}.dec"

echo -n "Decrypting..."
if out=$(gpg --no-tty --output "$decrypted_script" --decrypt "$encrypted_script" 2>&1); then
    echo "OK"

    run_script=$encrypted_script
    mv -f "$decrypted_script" "$run_script" || exit 1

    if ! chmod +x "$run_script" || ! chown "$user_name" "$run_script"; then
        echo "Failed to set permissions" >&2
        exit 1
    fi
else
    echo "Failed"
    echo "$out" >&2
    [[ ! -f $decrypted_script ]] || rm "$decrypted_script"
    exit 1
fi

