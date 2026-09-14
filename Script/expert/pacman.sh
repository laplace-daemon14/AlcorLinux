#!/usr/bin/env bash
set -e

CONTAINER="algol"

REAL_USER="${SUDO_USER:-$USER}"

if [ -z "$REAL_USER" ] || [ "$REAL_USER" = "root" ]; then
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
        if sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- pacman -Si "$PKG" &>/dev/null; then
            echo "[+] [Alcor Router] '$PKG' detected as a cybersecurity tool!"
            echo "[*] Installing into '$CONTAINER' container..."
            
            sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- sudo pacman -S --needed --noconfirm "$PKG"
            
            echo "[*] Integrating '$PKG' into the host system (distrobox-export)..."
            
            if sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- pacman -Ql "$PKG" | grep -E "\.desktop$" &>/dev/null; then
                sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- distrobox-export --app "$PKG"
            else
                sudo -u "$REAL_USER" mkdir -p /home/"$REAL_USER"/.local/bin
                sudo -u "$REAL_USER" distrobox enter "$CONTAINER" -- distrobox-export --bin /usr/bin/"$PKG" --export-path /home/"$REAL_USER"/.local/bin
            fi
            
            echo "[+] [Alcor Router] '$PKG' successfully installed and tunneled!"
            exit 0
        fi
    fi
fi

exec /usr/bin/pacman "$@"
