#!/usr/bin/env bash
set -e

CONTAINER_NAME="algol"

if distrobox list | grep -qw "$CONTAINER_NAME"; then
    echo "[+] [Alcor] '$CONTAINER_NAME' container already exists. Skipping initialization."
    exit 0
fi

echo "[*] [Alcor] Deploying 'algol' rootless cyber security environment..."
distrobox-create --image docker.io/library/archlinux:latest --name "$CONTAINER_NAME" --yes

echo "[*] [Alcor] Starting container for the first time..."
distrobox-enter --name "$CONTAINER_NAME" -- echo "Container is active."

echo "[*] [Alcor] Waiting for system services to settle..."
sleep 2

echo "[!] [Alcor] Configuring BlackArch repositories inside the container..."
distrobox-enter --name "$CONTAINER_NAME" -- bash -c '
    set -e
    
    curl -s -O https://blackarch.org
    chmod +x strap.sh
    
    sudo ./strap.sh < /dev/null
    rm strap.sh
    
    sudo pacman -Syy --noconfirm
'

echo "[+] [Alcor] 'algol' environment and BlackArch repo successfully deployed!"
