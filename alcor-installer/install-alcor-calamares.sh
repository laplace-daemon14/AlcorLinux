#!/usr/bin/env bash
set -Eeuo pipefail

CALAMARES_ROOT="${CALAMARES_ROOT:-}"
CALAMARES_CONFIG_DIR="${CALAMARES_ROOT%/}/etc/calamares"
CALAMARES_LOCAL_MODULE_DIR="$CALAMARES_CONFIG_DIR/modules"
if [[ -d "$CALAMARES_LOCAL_MODULE_DIR" ]]; then
    CALAMARES_MODULE_DIR="$CALAMARES_LOCAL_MODULE_DIR"
else
    CALAMARES_MODULE_DIR="$CALAMARES_ROOT/usr/share/calamares/modules"
fi
ALCOR_LIB_DIR="$CALAMARES_ROOT/usr/local/lib/alcor"
ALCOR_APP_DIR="$CALAMARES_ROOT/opt/alcor-installer"
ALCOR_BIN_DIR="$CALAMARES_ROOT/usr/local/bin"
SKEL_DESKTOP_DIR="$CALAMARES_ROOT/etc/skel/Desktop"
SETTINGS_FILE="$CALAMARES_CONFIG_DIR/settings.conf"
WELCOME_FILE="$CALAMARES_CONFIG_DIR/modules/welcome.conf"
UNPACKFS_FILE="$CALAMARES_CONFIG_DIR/modules/unpackfs.conf"
BRANDING_DIR="$CALAMARES_CONFIG_DIR/branding/alcor"
BLACKARCH_BRANDING_DIR="$CALAMARES_CONFIG_DIR/branding/blackarch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "[!] Run this script as root." >&2
    exit 1
fi

required_files=(
    alcor_frontend.py
    alcor_backend.sh
    algol-init
    alcor-firstboot
    alcor-firstboot.service
    alcor-firstboot.timer
    pacman
    alcor-installer
    alcor-install
    alcor-install.desktop
    calamares/modules/alcor_backend.conf
)
for required_file in "${required_files[@]}"; do
    if [[ ! -f "$SCRIPT_DIR/$required_file" ]]; then
        echo "[!] [Alcor] Required installer file is missing: $SCRIPT_DIR/$required_file" >&2
        exit 2
    fi
done

download_blackarch_key_file() {
    local strap_path="$1"
    local key_file="$2"
    local trusted_fingerprints
    local fingerprint
    local trusted_key_found=false

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --connect-timeout 10 --max-time 60 \
            https://raw.githubusercontent.com/BlackArch/blackarch-keyring/master/blackarch.gpg \
            -o "$key_file"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --timeout=60 --tries=1 \
            -O "$key_file" \
            https://raw.githubusercontent.com/BlackArch/blackarch-keyring/master/blackarch.gpg
    else
        echo "[!] [Alcor] curl or wget is required to download the BlackArch key file." >&2
        return 1
    fi

    trusted_fingerprints="$(sed -n '/^KEYRING_SIGNERS=/,/^$/p' "$strap_path" |
        grep -Eo '[[:xdigit:]]{40}' || true)"
    if [[ -z "$trusted_fingerprints" ]]; then
        echo "[!] [Alcor] Could not read trusted signer fingerprints from BlackArch strap.sh." >&2
        return 1
    fi

    while IFS= read -r fingerprint; do
        if gpg --batch --show-keys --with-colons --fingerprint "$key_file" 2>/dev/null |
            grep -Fq "$fingerprint"; then
            trusted_key_found=true
            break
        fi
    done <<< "$trusted_fingerprints"

    if [[ "$trusted_key_found" != true ]]; then
        echo "[!] [Alcor] The downloaded BlackArch key file does not contain a trusted signer key." >&2
        return 1
    fi
}

install_blackarch_pacman_keys() {
    local strap_path="$1"
    local key_file="$2"
    local trusted_fingerprints
    local fingerprint

    trusted_fingerprints="$(sed -n '/^KEYRING_SIGNERS=/,/^$/p' "$strap_path" |
        grep -Eo '[[:xdigit:]]{40}' || true)"
    if [[ -z "$trusted_fingerprints" ]]; then
        echo "[!] [Alcor] Could not read trusted signer fingerprints from BlackArch strap.sh." >&2
        return 1
    fi

    echo "[*] [Alcor] Downloading and validating the official BlackArch key file."
    download_blackarch_key_file "$strap_path" "$key_file"
    echo "[*] [Alcor] Importing BlackArch signing keys into pacman's keyring."
    pacman-key --init
    pacman-key --add "$key_file"
    while IFS= read -r fingerprint; do
        echo "[*] [Alcor] Locally trusting BlackArch signer $fingerprint."
        pacman-key --lsign-key "$fingerprint"
        if ! pacman-key --list-keys "$fingerprint" >/dev/null 2>&1; then
            echo "[!] [Alcor] BlackArch signer $fingerprint is not present in pacman's keyring after import." >&2
            return 1
        fi
    done <<< "$trusted_fingerprints"
    echo "[+] [Alcor] BlackArch signing keys were imported and locally trusted."
}

patch_blackarch_strap_for_key_file() {
    local strap_path="$1"

    if ! grep -qF 'Could not import downloaded BlackArch keyring' "$strap_path"; then
        sed -i '/^  mkdir -m 700 "$GNUPGHOME"$/a\
\
  if [ -n "${BLACKARCH_KEY_FILE:-}" ]; then\
gpg --batch --import "$BLACKARCH_KEY_FILE" || err "Could not import downloaded BlackArch keyring"\
  fi' "$strap_path"
    fi
    if ! grep -qF 'gpg --list-keys "$fpr"' "$strap_path"; then
        sed -i '/^  for fpr in \$KEYRING_SIGNERS; do$/a\
gpg --list-keys "$fpr" > /dev/null 2>&1 && continue' "$strap_path"
    fi

    if ! grep -qF 'Could not import downloaded BlackArch keyring' "$strap_path" ||
        ! grep -qF 'gpg --list-keys "$fpr"' "$strap_path"; then
        echo "[!] [Alcor] Failed to prepare BlackArch strap.sh for the downloaded key file." >&2
        return 1
    fi
}

run_blackarch_strap_with_fallback() {
    local strap_path="$1"
    local key_file="$2"
    local bootstrap_pid
    local elapsed
    local choice
    local status

    if ! command -v setsid >/dev/null 2>&1; then
        echo "[!] [Alcor] setsid is required to safely stop a timed-out BlackArch setup attempt." >&2
        return 1
    fi

    setsid env PATH=/usr/bin:/bin bash "$strap_path" &
    bootstrap_pid=$!

    for ((elapsed = 0; elapsed < 90; elapsed++)); do
        if ! kill -0 "$bootstrap_pid" 2>/dev/null; then
            if wait "$bootstrap_pid"; then
                return 0
            else
                return $?
            fi
        fi
        sleep 1
    done

    if ! kill -0 "$bootstrap_pid" 2>/dev/null; then
        if wait "$bootstrap_pid"; then
            return 0
        else
            return $?
        fi
    fi

    if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
        echo "[!] [Alcor] BlackArch setup is still running after 1 minute 30 seconds, but no terminal is available for a prompt; continuing the current attempt."
        if wait "$bootstrap_pid"; then
            return 0
        else
            return $?
        fi
    fi

    while true; do
        printf '[Alcor] BlackArch setup is still running after 1 minute 30 seconds. Download and import the BlackArch key file, then retry? [y/N]: ' > /dev/tty
        if ! IFS= read -r choice < /dev/tty; then
            choice=n
        fi
        case "$choice" in
            [yY]|[yY][eE][sS])
                if ! kill -0 "$bootstrap_pid" 2>/dev/null; then
                    if wait "$bootstrap_pid"; then
                        return 0
                    else
                        return $?
                    fi
                fi
                kill -TERM -- "-$bootstrap_pid" 2>/dev/null || kill -TERM "$bootstrap_pid" 2>/dev/null || true
                wait "$bootstrap_pid" 2>/dev/null || true
                download_blackarch_key_file "$strap_path" "$key_file" || return 1
                patch_blackarch_strap_for_key_file "$strap_path" || return 1
                echo "[*] [Alcor] Retrying BlackArch setup with the downloaded key file."
                setsid env PATH=/usr/bin:/bin BLACKARCH_KEY_FILE="$key_file" \
                    bash "$strap_path" &
                bootstrap_pid=$!
                if wait "$bootstrap_pid"; then
                    return 0
                else
                    status=$?
                    return "$status"
                fi
                ;;
            ""|[nN]|[nN][oO])
                if wait "$bootstrap_pid"; then
                    return 0
                else
                    return $?
                fi
                ;;
            *)
                printf 'Please answer y or n. Continuing the current attempt unless you choose y.\n' > /dev/tty
                ;;
        esac
    done
}

ensure_live_blackarch_repo_config() {
    local mirrorlist_path="/etc/pacman.d/blackarch-mirrorlist"
    local mirrorlist_url="https://blackarch.org/blackarch-mirrorlist"

    if [[ ! -s "$mirrorlist_path" ]]; then
        echo "[*] [Alcor] BlackArch strap did not configure its mirror list; fetching it directly."
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL --connect-timeout 10 --max-time 60 "$mirrorlist_url" -o "$mirrorlist_path"
        elif command -v wget >/dev/null 2>&1; then
            wget -q --timeout=60 --tries=1 -O "$mirrorlist_path" "$mirrorlist_url"
        else
            echo "[!] [Alcor] curl or wget is required to fetch the BlackArch mirror list." >&2
            return 1
        fi
    fi

    if ! grep -qE '^[[:space:]]*\[blackarch\][[:space:]]*$' /etc/pacman.conf; then
        printf '\n[blackarch]\nInclude = %s\n' "$mirrorlist_path" >> /etc/pacman.conf
    fi
}

ensure_live_blackarch_repo() {
    local temp_dir
    local repo_was_configured=false
    temp_dir="$(mktemp -d)"
    trap 'rm -rf "$temp_dir"' RETURN

    if grep -qE '^\[blackarch\][[:space:]]*$' /etc/pacman.conf; then
        repo_was_configured=true
        echo "[+] [Alcor] BlackArch repository is already enabled in Live."
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://blackarch.org/strap.sh -o "$temp_dir/strap.sh"
        elif command -v wget >/dev/null 2>&1; then
            wget -qO "$temp_dir/strap.sh" https://blackarch.org/strap.sh
        else
            echo "[!] [Alcor] curl or wget is required to check the BlackArch signing keys." >&2
            return 1
        fi
    else
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://blackarch.org/strap.sh -o "$temp_dir/strap.sh"
        elif command -v wget >/dev/null 2>&1; then
            wget -qO "$temp_dir/strap.sh" https://blackarch.org/strap.sh
        else
            echo "[!] [Alcor] curl or wget is required to add the BlackArch repository." >&2
            return 1
        fi
    fi

    chmod 0755 "$temp_dir/strap.sh"
    if [[ "$repo_was_configured" != true ]]; then
        if ! grep -q '^pacman_upgrade()$' "$temp_dir/strap.sh"; then
            echo "[!] [Alcor] BlackArch strap.sh has an unexpected upgrade function; refusing to run it without a non-interactive upgrade." >&2
            return 1
        fi
        sed -i '/^pacman_upgrade()$/,/^}/c\
pacman_upgrade()\
{\
  echo "[!] Skipping full system upgrade as requested."\
}' "$temp_dir/strap.sh"
        if ! grep -qF 'Skipping full system upgrade as requested.' "$temp_dir/strap.sh"; then
            echo "[!] [Alcor] Failed to disable the BlackArch full system upgrade." >&2
            return 1
        fi
    fi
    if [[ "$repo_was_configured" != true ]]; then
        echo "[*] [Alcor] Initializing the BlackArch keyring without upgrading the Live system."
        if ! (cd / && run_blackarch_strap_with_fallback "$temp_dir/strap.sh" "$temp_dir/blackarch.gpg"); then
            echo "[!] [Alcor] BlackArch keyring setup failed. Check network access to blackarch.org and the configured keyservers." >&2
            return 1
        fi
    fi
    ensure_live_blackarch_repo_config
    if ! grep -qE '^[[:space:]]*\[blackarch\][[:space:]]*$' /etc/pacman.conf; then
        echo "[!] [Alcor] BlackArch repository configuration could not be added to /etc/pacman.conf." >&2
        return 1
    fi
    install_blackarch_pacman_keys "$temp_dir/strap.sh" "$temp_dir/blackarch.gpg"
    echo "[*] [Alcor] Synchronizing BlackArch package databases before checking the keyring package."
    pacman -Syy --noconfirm
    if [[ ! -s /var/lib/pacman/sync/blackarch.db ]]; then
        echo "[!] [Alcor] BlackArch database is still missing after pacman synchronization; refusing to continue." >&2
        return 1
    fi
    if ! pacman -Q blackarch-keyring >/dev/null 2>&1; then
        echo "[*] [Alcor] Installing the BlackArch keyring package."
        pacman -S --needed --noconfirm blackarch-keyring
    fi
    echo "[+] [Alcor] BlackArch repository added to the Live system."
}

ensure_live_blackarch_repo

echo "[*] [Alcor] Checking the Live GUI dependency..."
if ! /usr/bin/python3 -c 'from PyQt6.QtWidgets import QApplication' >/dev/null 2>&1; then
    echo "[!] [Alcor] A compatible PyQt6 is missing from the Live image." >&2
    echo "[!] Add python-pyqt6 to the ArchISO package profile and rebuild the image; do not install it from rolling repositories at runtime." >&2
    exit 1
fi
echo "[+] [Alcor] Live PyQt6 dependency is available."

disable_live_os_prober() {
    local os_prober_path
    os_prober_path="$(command -v os-prober || true)"
    if [[ -z "$os_prober_path" ]]; then
        echo "[+] [Alcor] os-prober is not installed in Live."
        return 0
    fi
    if [[ "$os_prober_path" == *.alcor-disabled ]]; then
        echo "[+] [Alcor] os-prober is already disabled in Live."
        return 0
    fi
    mv "$os_prober_path" "${os_prober_path}.alcor-disabled"
    echo "[+] [Alcor] Disabled Live os-prober for single-disk installation."
}

disable_live_os_prober

if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "[*] [Alcor] Calamares is missing; installing it from BlackArch on Live..."
    /usr/bin/pacman -S --needed --noconfirm calamares blackarch-config-calamares
fi

if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "[!] [Alcor] Calamares settings file not found after installation: $SETTINGS_FILE" >&2
    echo "[!] Confirm that the Live system has the BlackArch repository enabled." >&2
    exit 1
fi

install -d "$ALCOR_LIB_DIR" "$CALAMARES_MODULE_DIR" "$CALAMARES_LOCAL_MODULE_DIR"

# Configure Calamares to remove the copied Live account from the target system.
# This runs after unpackfs and before the users job creates the selected account.
REMOVEUSER_CONFIG="$CALAMARES_LOCAL_MODULE_DIR/removeuser.conf"
if [[ -f "$REMOVEUSER_CONFIG" && ! -f "$REMOVEUSER_CONFIG.alcor-backup" ]]; then
    cp -a "$REMOVEUSER_CONFIG" "$REMOVEUSER_CONFIG.alcor-backup"
fi
printf '%s\n' '---' 'username: alcor' > "$REMOVEUSER_CONFIG"
chmod 0644 "$REMOVEUSER_CONFIG"
echo "[+] [Alcor] Calamares removeuser configured for the copied Live account."
install_shell_script() {
    local source_path="$1"
    local target_path="$2"
    sed 's/\r$//' "$source_path" > "$target_path.tmp"
    install -m 0755 "$target_path.tmp" "$target_path"
    rm -f "$target_path.tmp"
}

install_shell_script "$SCRIPT_DIR/alcor_backend.sh" "$ALCOR_LIB_DIR/alcor_backend.sh"
install_shell_script "$SCRIPT_DIR/algol-init" "$ALCOR_LIB_DIR/algol-init"
install_shell_script "$SCRIPT_DIR/alcor-firstboot" "$ALCOR_LIB_DIR/alcor-firstboot"
install -m 0644 "$SCRIPT_DIR/alcor-firstboot.service" \
    "$ALCOR_LIB_DIR/alcor-firstboot.service"
install -m 0644 "$SCRIPT_DIR/alcor-firstboot.timer" \
    "$ALCOR_LIB_DIR/alcor-firstboot.timer"
install_shell_script "$SCRIPT_DIR/pacman" "$ALCOR_LIB_DIR/pacman"
install -d "$ALCOR_APP_DIR" "$SKEL_DESKTOP_DIR"
install -m 0644 "$SCRIPT_DIR/alcor_frontend.py" "$ALCOR_APP_DIR/alcor_frontend.py"
for image in red_alcor.png blue_alcor.png purple_alcor.png expert_alcor.png; do
    install -m 0644 "$SCRIPT_DIR/$image" "$ALCOR_APP_DIR/$image"
done
install_shell_script "$SCRIPT_DIR/alcor-installer" "$ALCOR_BIN_DIR/alcor-installer"
install_shell_script "$SCRIPT_DIR/alcor-install" "$ALCOR_BIN_DIR/alcor-install"
install -m 0644 "$SCRIPT_DIR/alcor-install.desktop" \
    "$SKEL_DESKTOP_DIR/alcor-install.desktop"
install -d "$ALCOR_LIB_DIR/installer"
install -m 0644 "$SCRIPT_DIR/alcor_frontend.py" "$ALCOR_LIB_DIR/installer/alcor_frontend.py"
for installer_file in red_alcor.png blue_alcor.png purple_alcor.png expert_alcor.png; do
    install -m 0644 "$SCRIPT_DIR/$installer_file" \
        "$ALCOR_LIB_DIR/installer/$installer_file"
done
install_shell_script "$SCRIPT_DIR/alcor-installer" "$ALCOR_LIB_DIR/installer/alcor-installer"
install_shell_script "$SCRIPT_DIR/alcor-install" "$ALCOR_LIB_DIR/installer/alcor-install"
install -m 0644 "$SCRIPT_DIR/alcor-install.desktop" \
    "$ALCOR_LIB_DIR/installer/alcor-install.desktop"

LIVE_USER="${SUDO_USER:-}"
if [[ -z "$LIVE_USER" || "$LIVE_USER" == "root" ]]; then
    LIVE_USER="$(id -un)"
fi
LIVE_HOME="$(getent passwd "$LIVE_USER" | cut -d: -f6 || true)"
if [[ -n "$LIVE_HOME" && -d "$LIVE_HOME" ]]; then
    install -d "$LIVE_HOME/Desktop"
    install -o "$LIVE_USER" -m 0644 "$SCRIPT_DIR/alcor-install.desktop" \
        "$LIVE_HOME/Desktop/alcor-install.desktop"
    echo "[+] [Alcor] Live desktop launcher installed for $LIVE_USER."
fi
if [[ -f "$CALAMARES_MODULE_DIR/alcor_backend.conf" ]]; then
    cp -a "$CALAMARES_MODULE_DIR/alcor_backend.conf" \
        "$CALAMARES_MODULE_DIR/alcor_backend.conf.alcor-backup"
fi
install -m 0644 "$SCRIPT_DIR/calamares/modules/alcor_backend.conf" \
    "$CALAMARES_MODULE_DIR/alcor_backend.conf"

if [[ -f "$WELCOME_FILE" ]]; then
    if [[ ! -f "$WELCOME_FILE.alcor-backup" ]]; then
        cp -a "$WELCOME_FILE" "$WELCOME_FILE.alcor-backup"
    fi
    sed -i -E 's/requiredStorage:[[:space:]]*[0-9.]+/requiredStorage:    30.0/' "$WELCOME_FILE"
    if grep -qE '^[[:space:]]*showDonateUrl:' "$WELCOME_FILE"; then
        sed -i -E \
            's|^[[:space:]]*showDonateUrl:.*$|showDonateUrl: "https://alcorlinux.netlify.app/"|' \
            "$WELCOME_FILE"
    else
        printf '\nshowDonateUrl: "https://alcorlinux.netlify.app/"\n' >> "$WELCOME_FILE"
    fi
    if grep -qE '^[[:space:]]*showSupportUrl:' "$WELCOME_FILE"; then
        sed -i -E \
            's|^[[:space:]]*showSupportUrl:.*$|showSupportUrl: "https://alcorlinux.netlify.app/"|' \
            "$WELCOME_FILE"
    else
        printf '\nshowSupportUrl: "https://alcorlinux.netlify.app/"\n' >> "$WELCOME_FILE"
    fi
    echo "[+] [Alcor] Calamares donate and support links configured."
fi

ARCHISO_MOUNT="$CALAMARES_ROOT/run/archiso/bootmnt"
if [[ -f "$UNPACKFS_FILE" && -d "$ARCHISO_MOUNT" ]]; then
    AIROOTFS_SOURCE="$(find "$ARCHISO_MOUNT" -type f -name 'airootfs.sfs' -print -quit)"
    if [[ -z "$AIROOTFS_SOURCE" ]]; then
        echo "[!] [Alcor] Could not find the Live airootfs.sfs under $ARCHISO_MOUNT" >&2
        exit 1
    fi
    ISO_ROOT="${AIROOTFS_SOURCE%/x86_64/airootfs.sfs}"
    VMLINUX_SOURCE="$(find "$ISO_ROOT" -type f -name 'vmlinuz*' -print -quit)"
    if [[ -z "$VMLINUX_SOURCE" ]]; then
        echo "[!] [Alcor] Could not find the Live kernel under $ISO_ROOT" >&2
        exit 1
    fi
    AMD_UCODE_SOURCE="$(find "$ISO_ROOT" -type f -name 'amd-ucode.img' -print -quit)"
    INTEL_UCODE_SOURCE="$(find "$ISO_ROOT" -type f -name 'intel-ucode.img' -print -quit)"
    if [[ ! -f "$UNPACKFS_FILE.alcor-backup" ]]; then
        cp -a "$UNPACKFS_FILE" "$UNPACKFS_FILE.alcor-backup"
    fi
    sed -i -E "s|^[[:space:]]*-[[:space:]]*source:.*airootfs\.sfs.*$|    - source: \"$AIROOTFS_SOURCE\"|" "$UNPACKFS_FILE"
    sed -i -E "s|^[[:space:]]*-[[:space:]]*source:.*vmlinuz[^\"]*.*$|    - source: \"$VMLINUX_SOURCE\"|" "$UNPACKFS_FILE"
    if [[ -n "$AMD_UCODE_SOURCE" ]]; then
        sed -i -E "s|^[[:space:]]*-[[:space:]]*source:.*amd-ucode\.img.*$|    - source: \"$AMD_UCODE_SOURCE\"|" "$UNPACKFS_FILE"
    else
        sed -i '/source:.*amd-ucode\.img/,/weight:/d' "$UNPACKFS_FILE"
    fi
    if [[ -n "$INTEL_UCODE_SOURCE" ]]; then
        sed -i -E "s|^[[:space:]]*-[[:space:]]*source:.*intel-ucode\.img.*$|    - source: \"$INTEL_UCODE_SOURCE\"|" "$UNPACKFS_FILE"
    else
        sed -i '/source:.*intel-ucode\.img/,/weight:/d' "$UNPACKFS_FILE"
    fi
    sed -i 's/""/"/g' "$UNPACKFS_FILE"
    echo "[+] [Alcor] Calamares Live source: $ISO_ROOT"
    echo "[+] [Alcor] Calamares Live kernel: $VMLINUX_SOURCE"
fi

if [[ -d "$BLACKARCH_BRANDING_DIR" ]]; then
    install -d "$BRANDING_DIR"
    cp -a "$BLACKARCH_BRANDING_DIR/." "$BRANDING_DIR/"
    mapfile -t branding_images < <(find "$BRANDING_DIR" -type f -iname '*.png' -printf '%f\n')
    find "$BRANDING_DIR" -type f -iname '*.png' -delete
    find "$BRANDING_DIR" -type f \( -name '*.desc' -o -name '*.qss' \) -exec \
        sed -i -e 's/BlackArch Linux/Alcor GNU\/Linux/g' -e 's/BlackArch/Alcor/g' \
            -e 's/blackarch/alcor/g' {} +
    if [[ -f "$SCRIPT_DIR/red_alcor.png" ]]; then
        for image_name in "${branding_images[@]}" logo.png logo-calamares.png; do
            install -m 0644 "$SCRIPT_DIR/red_alcor.png" "$BRANDING_DIR/$image_name"
        done
    fi
    echo "[+] [Alcor] Calamares branding prepared."
fi

if [[ -f "$SETTINGS_FILE.alcor-backup" ]] && grep -qE '^sequence:[[:space:]]*$' "$SETTINGS_FILE.alcor-backup"; then
    cp -a "$SETTINGS_FILE.alcor-backup" "$SETTINGS_FILE"
elif ! grep -qE '^sequence:[[:space:]]*$' "$SETTINGS_FILE"; then
    echo "[!] [Alcor] Calamares settings has no sequence and no valid backup is available." >&2
    exit 1
else
    cp -a "$SETTINGS_FILE" "$SETTINGS_FILE.alcor-backup"
fi

if ! grep -qE '^[[:space:]]*-[[:space:]]*umount[[:space:]]*$' "$SETTINGS_FILE"; then
    echo "[!] Could not find the Calamares umount step in $SETTINGS_FILE" >&2
    echo "[!] Scripts were installed, but the settings file was not changed." >&2
    exit 1
fi

# Ensure removeuser runs in the exec phase, after unpackfs and before users.
# Rebuild from the pristine settings backup above, then insert exactly one entry.
sed -i -E '/^[[:space:]]*-[[:space:]]*removeuser(@[^[:space:]]+)?[[:space:]]*$/d' "$SETTINGS_FILE"

if ! awk '
    /^sequence:[[:space:]]*$/ {
        in_sequence = 1
        in_exec = 0
        print
        next
    }

    in_sequence && /^[^[:space:]#-]/ {
        in_sequence = 0
        in_exec = 0
    }

    in_sequence && /^[[:space:]]*-[[:space:]]*show:[[:space:]]*$/ {
        in_exec = 0
        print
        next
    }

    in_sequence && /^[[:space:]]*-[[:space:]]*exec:[[:space:]]*$/ {
        in_exec = 1
        print
        next
    }

    {
        if (in_sequence && in_exec &&
            /^[[:space:]]*-[[:space:]]*unpackfs[[:space:]]*$/) {
            match($0, /^[[:space:]]*/)
            indent = substr($0, 1, RLENGTH)
            print
            print indent "- removeuser"
            inserted = 1
            next
        }
        print
    }

    END {
        if (!inserted) exit 1
    }
' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"; then
    rm -f "$SETTINGS_FILE.tmp"
    echo "[!] [Alcor] Could not place removeuser after unpackfs in the Calamares exec phase." >&2
    exit 1
fi
mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"

# Verify the job order: unpackfs -> removeuser -> users, all in exec.
if ! awk '
    /^sequence:[[:space:]]*$/ { in_sequence = 1; next }
    in_sequence && /^[^[:space:]#-]/ { in_sequence = 0; in_exec = 0 }
    in_sequence && /^[[:space:]]*-[[:space:]]*show:[[:space:]]*$/ { in_exec = 0; next }
    in_sequence && /^[[:space:]]*-[[:space:]]*exec:[[:space:]]*$/ { in_exec = 1; next }
    in_sequence && in_exec && /^[[:space:]]*-[[:space:]]*unpackfs[[:space:]]*$/ { unpackfs_line = NR }
    in_sequence && in_exec && /^[[:space:]]*-[[:space:]]*removeuser[[:space:]]*$/ { removeuser_line = NR }
    in_sequence && in_exec && /^[[:space:]]*-[[:space:]]*users[[:space:]]*$/ { users_line = NR }
    END {
        if (!(unpackfs_line && removeuser_line && users_line &&
              unpackfs_line < removeuser_line && removeuser_line < users_line)) exit 1
    }
' "$SETTINGS_FILE"; then
    echo "[!] [Alcor] Calamares removeuser ordering validation failed; expected unpackfs -> removeuser -> users." >&2
    exit 1
fi
echo "[+] [Alcor] Live account removal ordered after unpackfs and before user creation."

sed -i '/shellprocess@alcor_backend/d' "$SETTINGS_FILE"
sed -i '/^[[:space:]]*-[[:space:]]*packages[[:space:]]*$/d' "$SETTINGS_FILE"
sed -i '/^[[:space:]]*-[[:space:]]*initcpiocfg[[:space:]]*$/d' "$SETTINGS_FILE"
sed -i '/^[[:space:]]*-[[:space:]]*initcpio[[:space:]]*$/d' "$SETTINGS_FILE"
if ! grep -qE '^[[:space:]]*id:[[:space:]]*alcor_backend[[:space:]]*$' "$SETTINGS_FILE"; then
    awk '
        /^branding:/ && !inserted {
            print "- module:   shellprocess"
            print "  id:       alcor_backend"
            print "  config:   alcor_backend.conf"
            print "  weight:   10"
            inserted = 1
        }
        { print }
    ' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"
    mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
fi
sed -i '/^[[:space:]]*-[[:space:]]*grubcfg[[:space:]]*$/i\  - shellprocess@alcor_backend' "$SETTINGS_FILE"
sed -i -E 's/^branding:[[:space:]]*blackarch/branding: alcor/' "$SETTINGS_FILE"
rm -f "$CALAMARES_LOCAL_MODULE_DIR/shellprocess.conf"

if ! grep -qE '^[[:space:]]*-[[:space:]]*shellprocess@alcor_backend[[:space:]]*$' "$SETTINGS_FILE" || \
    ! grep -qE '^[[:space:]]*id:[[:space:]]*alcor_backend[[:space:]]*$' "$SETTINGS_FILE" || \
    ! grep -qE '^sequence:[[:space:]]*$' "$SETTINGS_FILE"; then
    echo "[!] [Alcor] Calamares backend instance was not installed correctly." >&2
    exit 1
fi

if [[ ! -s "$REMOVEUSER_CONFIG" ]] || ! grep -qx 'username: alcor' "$REMOVEUSER_CONFIG"; then
    echo "[!] [Alcor] Calamares removeuser configuration is missing or invalid." >&2
    exit 1
fi
if [[ "$(grep -Ec '^[[:space:]]*-[[:space:]]*removeuser[[:space:]]*$' "$SETTINGS_FILE")" -ne 1 ]]; then
    echo "[!] [Alcor] Calamares must contain exactly one removeuser job." >&2
    exit 1
fi

echo "[+] [Alcor] Backend enabled before initramfs and bootloader setup."
echo "[+] [Alcor] Backup: $SETTINGS_FILE.alcor-backup"
