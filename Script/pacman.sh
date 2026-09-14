#!/usr/bin/env bash
set -e

CONTAINER="algol"

if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER="$USER"
fi

if [ "$REAL_USER" = "root" ]; then
    REAL_USER="alcor"
fi

IS_SYNC=false
for arg in "$@"; do
    if [[ "$arg" == "-S" ]] || [[ "$arg" == "--sync" ]]; then
        IS_SYNC=true
        break
    fi
done

if [ "$IS_SYNC" = true ]; then
    PKG=""
    for arg in "$@"; do
        if [[ ! "$arg" =~ ^- ]]; then
            PKG="$arg"
            break
        fi
    done

    if [ -n "$PKG" ]; then
        if [ "$EUID" -eq 0 ]; then
            REPO_INFO=$(sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- pacman -Si "$PKG" 2>/dev/null || true)
        else
            REPO_INFO=$(distrobox enter "$CONTAINER" -- pacman -Si "$PKG" 2>/dev/null || true)
        fi
        
        if [[ -n "$REPO_INFO" ]]; then
            if [[ "$REPO_INFO" == *"blackarch"* ]] || \
               [[ "$REPO_INFO" == *"Groups"* && "$REPO_INFO" == *"blackarch-"* ]] || \
               ([[ "$REPO_INFO" =~ (security|scanner|packet|exploit|vulnerability|sniffer|crypto|injection|sqlmap) ]] && [[ ! "$PKG" =~ (firefox|chromium|libreoffice|jack) ]]); then
                
                echo "[!] [Alcor Router] '$PKG' verified as a cyber security package!"
                echo "[*] Installing inside '$CONTAINER' container..."
                
                if [ "$EUID" -eq 0 ]; then
                    sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- sudo pacman -S --needed --noconfirm "$PKG"
                    echo "[*] Exporting '$PKG' to the host system..."
                    if sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- pacman -Ql "$PKG" | grep -E "\.desktop$" &>/dev/null; then
                        sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- distrobox-export --app "$PKG"
                    else
                        sudo -u "$REAL_USER" mkdir -p /home/"$REAL_USER"/.local/bin
                        sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- distrobox-export --bin /usr/bin/"$PKG" --export-path /home/"$REAL_USER"/.local/bin
                    fi
                else
                    distrobox enter "$CONTAINER" -- sudo pacman -S --needed --noconfirm "$PKG"
                    echo "[*] Exporting '$PKG' to the host system..."
                    if distrobox enter "$CONTAINER" -- pacman -Ql "$PKG" | grep -E "\.desktop$" &>/dev/null; then
                        distrobox enter "$CONTAINER" -- distrobox-export --app "$PKG"
                    else
                        mkdir -p /home/"$REAL_USER"/.local/bin
                        distrobox enter "$CONTAINER" -- distrobox-export --bin /usr/bin/"$PKG" --export-path /home/"$REAL_USER"/.local/bin
                    fi
                fi
                
                echo "[+] [Alcor Router] '$PKG' successfully installed and exported!"
                exit 0
            fi
        fi
    fi
fi

if [ "$EUID" -ne 0 ]; then
    exec sudo /usr/bin/pacman "$@"
else
    exec /usr/bin/pacman "$@"
fi
