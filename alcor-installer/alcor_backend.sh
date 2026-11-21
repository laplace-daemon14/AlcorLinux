#!/usr/bin/env bash
set -Eeuo pipefail

TARGET_ROOT="${CALAMARES_TARGET:-/}"
SELECTION_FILE="${ALCOR_SELECTION_FILE:-/tmp/alcor_selection.txt}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${ALCOR_BACKEND_LOG:-/tmp/alcor-backend.log}"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "[*] [Alcor] Backend started: $(date -Is)"
echo "[*] [Alcor] CALAMARES_TARGET=${CALAMARES_TARGET:-unset}"

if [[ ! -f "$SELECTION_FILE" ]]; then
    latest_selection="$(find /tmp -maxdepth 1 -type f \
        -name 'alcor_selection_*.txt' -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr | awk 'NR == 1 { print $2 }')"
    if [[ -n "$latest_selection" && -f "$latest_selection" ]]; then
        SELECTION_FILE="$latest_selection"
        echo "[*] [Alcor] Resolved selection file: $SELECTION_FILE"
    fi
fi

if [[ -z "${CALAMARES_TARGET:-}" ]]; then
    for candidate in /tmp/calamares-root /tmp/target /target /mnt; do
        if [[ -d "$candidate/etc" && -d "$candidate/boot" && -f "$candidate/etc/fstab" ]]; then
            TARGET_ROOT="$candidate"
            break
        fi
    done
fi

if [[ "$TARGET_ROOT" == "/" ]]; then
    while read -r mountpoint filesystem; do
        if [[ ( "$filesystem" == "ext4" || "$filesystem" == "btrfs" ) && \
              "$mountpoint" != "/" && \
              -d "$mountpoint/etc" && -f "$mountpoint/etc/fstab" ]]; then
            TARGET_ROOT="$mountpoint"
            break
        fi
    done < <(findmnt -rn -o TARGET,FSTYPE 2>/dev/null || true)
fi

echo "[*] [Alcor] Resolved target root: $TARGET_ROOT"

if [[ "$TARGET_ROOT" != "/" && ! -d "$TARGET_ROOT" ]]; then
    echo "[!] Calamares target does not exist: $TARGET_ROOT" >&2
    exit 1
fi

if [[ "$TARGET_ROOT" == "/" ]]; then
    echo "[!] [Alcor] No Calamares target root was provided; refusing to modify Live root." >&2
    exit 1
fi

copy_live_grub_configuration() {
    local live_root="${ALCOR_LIVE_ROOT:-/}"
    local live_default="$live_root/etc/default/grub"
    local target_default="$TARGET_ROOT/etc/default/grub"
    local relative_path
    local live_path
    local target_path

    if [[ -f "$live_default" ]]; then
        install -d "$(dirname "$target_default")"
        if [[ -f "$target_default" && ! -e "$target_default.alcor-backup" ]]; then
            cp -a "$target_default" "$target_default.alcor-backup"
        fi
        cp -a "$live_default" "$target_default"
        echo "[+] [Alcor] Copied Live GRUB defaults."
    fi

    for relative_path in \
        etc/default/grub.d \
        etc/grub.d \
        usr/share/grub/themes \
        boot/grub/themes; do
        live_path="$live_root/$relative_path"
        target_path="$TARGET_ROOT/$relative_path"
        if [[ -d "$live_path" ]]; then
            install -d "$target_path"
            cp -an "$live_path/." "$target_path/"
            echo "[+] [Alcor] Merged Live GRUB files: /$relative_path"
        fi
    done

    if [[ -f "$live_root/boot/grub/grub.cfg" ]]; then
        echo "[*] [Alcor] Keeping the generated Live grub.cfg out of the target; Calamares will generate a target-specific configuration."
    fi
}

if [[ ! -f "$SELECTION_FILE" ]]; then
    echo "[!] Alcor selection file not found: $SELECTION_FILE" >&2
    exit 1
fi

KERNELS="$(sed -n 's/^KERNELS://p' "$SELECTION_FILE")"
if [[ -z "$KERNELS" ]]; then
    KERNELS="$(sed -n 's/^KERNEL://p' "$SELECTION_FILE")"
fi
IFS=',' read -r -a SELECTED_KERNELS <<< "$KERNELS"
if [[ "${#SELECTED_KERNELS[@]}" -eq 0 || -z "${SELECTED_KERNELS[0]}" ]]; then
    echo "[!] [Alcor] No kernel selection was provided." >&2
    exit 1
fi
for kernel in "${SELECTED_KERNELS[@]}"; do
    case "$kernel" in
        linux|linux-zen|linux-hardened|linux-lts) ;;
        *)
            echo "[!] [Alcor] Invalid kernel selection: $kernel" >&2
            exit 1
            ;;
    esac
done

DISPLAY_MANAGER="$(sed -n 's/^DISPLAY_MANAGER://p' "$SELECTION_FILE")"
DISPLAY_MANAGER="${DISPLAY_MANAGER:-lightdm}"
case "$DISPLAY_MANAGER" in
    lightdm) ;;
    *)
        echo "[!] [Alcor] Unsupported display manager selection: ${DISPLAY_MANAGER:-empty}. LightDM with XFCE is currently supported." >&2
        exit 1
        ;;
esac

FIREWALL="$(sed -n 's/^FIREWALL://p' "$SELECTION_FILE")"
FIREWALL="${FIREWALL:-none}"
case "$FIREWALL" in
    none|ufw) ;;
    *)
        echo "[!] [Alcor] Unsupported firewall selection: $FIREWALL" >&2
        exit 1
        ;;
esac
COMMUNITY_HOST_PACKAGES=()
COMMUNITY_ALGOL_PACKAGES=()
COMMUNITY_HOST_CLI_TOOLS=()
COMMUNITY_ALGOL_CLI_TOOLS=()

COMMUNITY_HOST_SELECTION="$(
    sed -n 's/^COMMUNITY_HOST://p' "$SELECTION_FILE"
)"

COMMUNITY_ALGOL_SELECTION="$(
    sed -n 's/^COMMUNITY_ALGOL://p' "$SELECTION_FILE"
)"

parse_community_packages() {
    local target="$1"
    local raw="$2"
    local package
    local -a parsed=()
    local -A seen=()

    if [[ -z "$raw" ]]; then
        return 0
    fi

    IFS=',' read -r -a parsed <<< "$raw"

    for package in "${parsed[@]}"; do
        case "$package" in
            lightpacket|lightbpf|cza) ;;
            *)
                echo "[!] [Alcor] Unsupported Community package: $package" >&2
                return 1
                ;;
        esac

        if [[ -n "${seen[$package]:-}" ]]; then
            continue
        fi

        seen["$package"]=1

        case "$target:$package" in
            host:lightpacket|host:lightbpf)
                COMMUNITY_HOST_PACKAGES+=("$package")
                ;;
            algol:lightpacket|algol:lightbpf)
                COMMUNITY_ALGOL_PACKAGES+=("$package")
                ;;
            host:cza)
                COMMUNITY_HOST_CLI_TOOLS+=("$package")
                ;;
            algol:cza)
                COMMUNITY_ALGOL_CLI_TOOLS+=("$package")
                ;;
        esac
    done
}

parse_community_packages host "$COMMUNITY_HOST_SELECTION"
parse_community_packages algol "$COMMUNITY_ALGOL_SELECTION"

echo "[*] [Alcor] Community Host Python packages: ${COMMUNITY_HOST_PACKAGES[*]:-none}"
echo "[*] [Alcor] Community Algol Python packages: ${COMMUNITY_ALGOL_PACKAGES[*]:-none}"
echo "[*] [Alcor] Community Host CLI tools: ${COMMUNITY_HOST_CLI_TOOLS[*]:-none}"
echo "[*] [Alcor] Community Algol CLI tools: ${COMMUNITY_ALGOL_CLI_TOOLS[*]:-none}"

DISPLAY_MANAGER_PACKAGES=("$DISPLAY_MANAGER")
DISPLAY_MANAGER_PACKAGES+=(
    zsh
    distrobox
    podman
    lightdm-gtk-greeter
    xorg-server
    xfce4-session
    xfce4-panel
    xfdesktop
    xfwm4
    xfce4-settings
)
if (( ${#COMMUNITY_HOST_PACKAGES[@]} > 0 )); then
    DISPLAY_MANAGER_PACKAGES+=(python python-pip)
fi
if (( ${#COMMUNITY_HOST_CLI_TOOLS[@]} > 0 )); then
    DISPLAY_MANAGER_PACKAGES+=(curl)
fi
if [[ "$FIREWALL" == "ufw" ]]; then
    DISPLAY_MANAGER_PACKAGES+=(ufw)
fi

if [[ "$TARGET_ROOT" != "/" ]]; then
    if ! command -v arch-chroot >/dev/null 2>&1; then
        echo "[!] [Alcor] arch-chroot is required to install the kernel during Calamares." >&2
        exit 1
    fi
    normalize_mkinitcpio_presets() {
        rm -f "$TARGET_ROOT/etc/mkinitcpio.conf.d/archiso.conf"
        if [[ -d "$TARGET_ROOT/etc/mkinitcpio.conf.d" ]]; then
            find "$TARGET_ROOT/etc/mkinitcpio.conf.d" -maxdepth 1 \
                -type f -iname '*archiso*' -delete
        fi
        if [[ -f "$TARGET_ROOT/etc/mkinitcpio.conf" ]]; then
            sed -i '/archiso/d' "$TARGET_ROOT/etc/mkinitcpio.conf"
        fi
        if [[ -d "$TARGET_ROOT/etc/mkinitcpio.d" ]]; then
            find "$TARGET_ROOT/etc/mkinitcpio.d" -maxdepth 1 \
                -type f -name '*.preset' -delete
        else
            install -d "$TARGET_ROOT/etc/mkinitcpio.d"
        fi
    }

    echo "[*] [Alcor] Removing Live ArchISO mkinitcpio presets before kernel install."
    normalize_mkinitcpio_presets
    echo "[*] [Alcor] Initializing the target pacman keyring."
    arch-chroot "$TARGET_ROOT" bash -c '
        install -d -m 700 /etc/pacman.d/gnupg
        pacman-key --init
        pacman-key --populate archlinux
    '
    echo "[*] [Alcor] Installing selected host kernels into target: $KERNELS"
    arch-chroot "$TARGET_ROOT" pacman -Sy --needed --noconfirm --noscriptlet \
        "${SELECTED_KERNELS[@]}"
    echo "[*] [Alcor] Installing selected display manager into target: $DISPLAY_MANAGER"
    arch-chroot "$TARGET_ROOT" pacman -S --needed --noconfirm \
        "${DISPLAY_MANAGER_PACKAGES[@]}"
    if (( ${#COMMUNITY_HOST_PACKAGES[@]} > 0 )); then
            echo "[*] [Alcor] Installing Community Python libraries on Host..."
            arch-chroot "$TARGET_ROOT" python -m pip install \
                --disable-pip-version-check \
                --no-cache-dir \
                --only-binary=:all: \
                --break-system-packages \
                --prefix=/usr/local \
                "${COMMUNITY_HOST_PACKAGES[@]}"

            echo "[*] [Alcor] Registering the Host /usr/local Python package directory..."
            HOST_SYSTEM_SITE="$(arch-chroot "$TARGET_ROOT" /usr/bin/python -c \
                'import sysconfig; print(sysconfig.get_path("purelib"))')"
            HOST_LOCAL_SITE="$(arch-chroot "$TARGET_ROOT" /usr/bin/python -c \
                'import sysconfig; print(sysconfig.get_path("purelib", vars={"base": "/usr/local", "platbase": "/usr/local"}))')"

            if [[ -z "$HOST_SYSTEM_SITE" || -z "$HOST_LOCAL_SITE" || \
                  "$HOST_SYSTEM_SITE" != /* || "$HOST_LOCAL_SITE" != /usr/local/lib/* || \
                  ! -d "$TARGET_ROOT$HOST_LOCAL_SITE" ]]; then
                echo "[!] [Alcor] Could not determine or locate the Host Python package directories." >&2
                exit 1
            fi

            install -d "$TARGET_ROOT$HOST_SYSTEM_SITE"
            printf '%s\n' "$HOST_LOCAL_SITE" \
                > "$TARGET_ROOT$HOST_SYSTEM_SITE/alcor-local-prefix.pth"
            chmod 0644 "$TARGET_ROOT$HOST_SYSTEM_SITE/alcor-local-prefix.pth"

            echo "[*] [Alcor] Verifying Host Community Python distributions..."
            if ! arch-chroot "$TARGET_ROOT" /usr/bin/python -c '
import importlib.metadata as metadata
import sys

failed = False
for distribution in sys.argv[1:]:
    try:
        version = metadata.version(distribution)
    except metadata.PackageNotFoundError:
        print(f"[!] [Alcor] Host Python distribution not visible: {distribution}", file=sys.stderr)
        failed = True
    else:
        print(f"[+] [Alcor] Verified Host {distribution}=={version}")

raise SystemExit(1 if failed else 0)
' "${COMMUNITY_HOST_PACKAGES[@]}"; then
                echo "[!] [Alcor] Host Community library verification failed after registering /usr/local." >&2
                exit 1
            fi

            echo "[+] [Alcor] Host Community libraries installed and visible to Python."
    fi
    if (( ${#COMMUNITY_HOST_CLI_TOOLS[@]} > 0 )); then
        for community_tool in "${COMMUNITY_HOST_CLI_TOOLS[@]}"; do
            case "$community_tool" in
                cza)
                    echo "[*] [Alcor] Preparing CZA installer for the installed Host target."
                    cza_live_installer="$(mktemp /tmp/alcor-cza-installer.XXXXXX)"
                    if ! curl --fail --silent --show-error --location \
                        --connect-timeout 10 --max-time 120 \
                        "https://gitlab.com/ranonimolan/cza/-/raw/main/install.sh" \
                        -o "$cza_live_installer"; then
                        rm -f "$cza_live_installer"
                        echo "[!] [Alcor] Could not download the CZA upstream installer." >&2
                        exit 1
                    fi
                    if ! bash -n "$cza_live_installer"; then
                        rm -f "$cza_live_installer"
                        echo "[!] [Alcor] Downloaded CZA installer failed shell syntax validation." >&2
                        exit 1
                    fi
                    echo "[!] [Alcor] Executing the reviewed-by-user CZA installer in Host with --global."
                    # Feed the reviewed installer to Bash over stdin. Do not stage it
                    # under TARGET_ROOT/tmp: arch-chroot may expose a different /tmp
                    # mount namespace, making that path disappear inside the chroot.
                    if ! arch-chroot "$TARGET_ROOT" /usr/bin/bash -s -- --global < "$cza_live_installer"; then
                        rm -f "$cza_live_installer"
                        echo "[!] [Alcor] CZA installation failed in the Host target." >&2
                        exit 1
                    fi
                    rm -f "$cza_live_installer"
                    if ! arch-chroot "$TARGET_ROOT" /usr/bin/bash -c 'command -v cza >/dev/null'; then
                        echo "[!] [Alcor] CZA installer completed but the cza command was not found in Host." >&2
                        exit 1
                    fi
                    echo "[+] [Alcor] CZA installed system-wide in Host."
                    ;;
                *)
                    echo "[!] [Alcor] Unsupported Host Community CLI tool: $community_tool" >&2
                    exit 1
                    ;;
            esac
        done
    fi
    if [[ "$FIREWALL" == "ufw" ]]; then
        UFW_CONFIG="$TARGET_ROOT/etc/ufw/ufw.conf"
        UFW_DEFAULTS="$TARGET_ROOT/etc/default/ufw"
        UFW_SERVICE="$TARGET_ROOT/usr/lib/systemd/system/ufw.service"
        if [[ ! -f "$UFW_CONFIG" || ! -f "$UFW_DEFAULTS" || ! -f "$UFW_SERVICE" ]]; then
            echo "[!] [Alcor] UFW package did not install its expected config and service files." >&2
            exit 1
        fi
        for policy in DEFAULT_INPUT_POLICY DEFAULT_OUTPUT_POLICY DEFAULT_FORWARD_POLICY; do
            if ! grep -qE "^[[:space:]]*$policy=" "$UFW_DEFAULTS"; then
                echo "[!] [Alcor] UFW policy setting is missing: $policy" >&2
                exit 1
            fi
        done
        if ! grep -qE '^[[:space:]]*ENABLED=' "$UFW_CONFIG"; then
            echo "[!] [Alcor] UFW ENABLED setting is missing." >&2
            exit 1
        fi
        sed -i -E \
            -e 's/^[[:space:]]*DEFAULT_INPUT_POLICY=.*/DEFAULT_INPUT_POLICY="DROP"/' \
            -e 's/^[[:space:]]*DEFAULT_OUTPUT_POLICY=.*/DEFAULT_OUTPUT_POLICY="ACCEPT"/' \
            -e 's/^[[:space:]]*DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="DROP"/' \
            "$UFW_DEFAULTS"
        sed -i -E 's/^[[:space:]]*ENABLED=.*/ENABLED=yes/' "$UFW_CONFIG"
        if ! systemctl --root="$TARGET_ROOT" enable ufw.service; then
            echo "[!] [Alcor] Failed to enable ufw.service in the target." >&2
            exit 1
        fi
        echo "[+] [Alcor] UFW enabled: incoming denied, outgoing allowed."
    fi
    if [[ ! -f "$TARGET_ROOT/usr/lib/systemd/system/$DISPLAY_MANAGER.service" ]]; then
        echo "[!] [Alcor] Display manager service was not installed: $DISPLAY_MANAGER.service" >&2
        exit 1
    fi
    for other_manager in lightdm sddm gdm; do
        if [[ "$other_manager" != "$DISPLAY_MANAGER" ]] && {
            [[ -f "$TARGET_ROOT/usr/lib/systemd/system/$other_manager.service" ]] ||
            [[ -f "$TARGET_ROOT/etc/systemd/system/$other_manager.service" ]]
        }; then
            if ! systemctl --root="$TARGET_ROOT" disable "$other_manager.service"; then
                echo "[!] [Alcor] Failed to disable conflicting display manager: $other_manager.service" >&2
                exit 1
            fi
        fi
    done
    if ! systemctl --root="$TARGET_ROOT" enable "$DISPLAY_MANAGER.service"; then
        echo "[!] [Alcor] Failed to enable $DISPLAY_MANAGER.service in the target." >&2
        exit 1
    fi
    if [[ "$DISPLAY_MANAGER" == "lightdm" ]]; then
        if [[ ! -f "$TARGET_ROOT/usr/share/xgreeters/lightdm-gtk-greeter.desktop" ]]; then
            echo "[!] [Alcor] LightDM GTK greeter desktop file is missing." >&2
            exit 1
        fi
        if [[ ! -f "$TARGET_ROOT/usr/share/xsessions/xfce.desktop" ]]; then
            echo "[!] [Alcor] XFCE session desktop file is missing." >&2
            exit 1
        fi
        LIGHTDM_CONFIG="$TARGET_ROOT/etc/lightdm/lightdm.conf"
        install -d "$TARGET_ROOT/etc/lightdm"
        if [[ -f "$LIGHTDM_CONFIG" ]]; then
            cp -an "$LIGHTDM_CONFIG" "$LIGHTDM_CONFIG.alcor-backup"
        else
            : > "$LIGHTDM_CONFIG"
        fi
        if grep -qE '^\[Seat:\*\][[:space:]]*$' "$LIGHTDM_CONFIG"; then
            sed -i '/^\[Seat:\*\][[:space:]]*$/,/^\[/ {
                /^[[:space:]]*greeter-session[[:space:]]*=/d
                /^[[:space:]]*user-session[[:space:]]*=/d
            }' "$LIGHTDM_CONFIG"
            sed -i '/^\[Seat:\*\][[:space:]]*$/a\
greeter-session=lightdm-gtk-greeter\
user-session=xfce' "$LIGHTDM_CONFIG"
        else
            printf '\n[Seat:*]\ngreeter-session=lightdm-gtk-greeter\nuser-session=xfce\n' \
                >> "$LIGHTDM_CONFIG"
        fi
    fi
    if ! systemctl --root="$TARGET_ROOT" set-default graphical.target; then
        echo "[!] [Alcor] Failed to set graphical.target as the default target." >&2
        exit 1
    fi
    install -d "$TARGET_ROOT/etc/systemd/system/graphical.target.wants"
    ln -sfn "/usr/lib/systemd/system/$DISPLAY_MANAGER.service" \
        "$TARGET_ROOT/etc/systemd/system/graphical.target.wants/$DISPLAY_MANAGER.service"
    ln -sfn "/usr/lib/systemd/system/$DISPLAY_MANAGER.service" \
        "$TARGET_ROOT/etc/systemd/system/display-manager.service"
    ln -sfn /usr/lib/systemd/system/graphical.target \
        "$TARGET_ROOT/etc/systemd/system/default.target"
    if [[ "$(basename "$(readlink "$TARGET_ROOT/etc/systemd/system/default.target")")" \
          != "graphical.target" ]]; then
        echo "[!] [Alcor] Installed system default target is not graphical.target." >&2
        exit 1
    fi
    if [[ ! -L "$TARGET_ROOT/etc/systemd/system/graphical.target.wants/$DISPLAY_MANAGER.service" || \
          ! -L "$TARGET_ROOT/etc/systemd/system/display-manager.service" ]]; then
        echo "[!] [Alcor] Display manager is not linked to the installed graphical boot target." >&2
        exit 1
    fi
    echo "[+] [Alcor] $DISPLAY_MANAGER is linked to graphical.target and display-manager.service."

    copy_live_grub_configuration

    for kernel in "${SELECTED_KERNELS[@]}"; do
        cat > "$TARGET_ROOT/etc/mkinitcpio.d/$kernel.preset" <<EOF
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-$kernel"

PRESETS=('default' 'fallback')

default_image="/boot/initramfs-$kernel.img"
fallback_image="/boot/initramfs-$kernel-fallback.img"
EOF
    done
    if [[ -f "$TARGET_ROOT/etc/mkinitcpio.conf" ]]; then
        if (( ${#SELECTED_KERNELS[@]} > 1 )) || \
           [[ ! -f "$TARGET_ROOT/usr/lib/initcpio/install/plymouth" ]]; then
            sed -i -E 's/[[:space:]]*plymouth([[:space:]]|$)/ /g' \
                "$TARGET_ROOT/etc/mkinitcpio.conf"
            sed -i -E 's/[[:space:]]+/ /g' "$TARGET_ROOT/etc/mkinitcpio.conf"
            if [[ -f "$TARGET_ROOT/etc/default/grub" ]]; then
                sed -i -E '/^GRUB_CMDLINE_LINUX_DEFAULT=/ {
                    s/[[:space:]]quiet([[:space:]]|")/ \1/g
                    s/[[:space:]]splash([[:space:]]|")/ \1/g
                }' "$TARGET_ROOT/etc/default/grub"
            fi
            echo "[*] [Alcor] Disabled Plymouth splash for reliable kernel boot."
        fi
    fi
    echo "[*] [Alcor] Building the installed kernel initramfs."
    arch-chroot "$TARGET_ROOT" mkinitcpio -P
    for kernel in "${SELECTED_KERNELS[@]}"; do
        for image in "/boot/initramfs-$kernel.img" \
                     "/boot/initramfs-$kernel-fallback.img"; do
            if [[ ! -s "$TARGET_ROOT$image" ]]; then
                echo "[!] [Alcor] Missing generated initramfs image: $image" >&2
                exit 1
            fi
        done
    done
    echo "[*] [Alcor] Normalized mkinitcpio presets for installed kernels: $KERNELS"
fi

install -d "$TARGET_ROOT/etc/alcor" "$TARGET_ROOT/usr/local/sbin" "$TARGET_ROOT/usr/local/bin"
install -m 0644 "$SELECTION_FILE" "$TARGET_ROOT/etc/alcor/selection.txt"
install -m 0755 "$SCRIPT_DIR/algol-init" "$TARGET_ROOT/usr/local/sbin/alcor-algol-init"
install -m 0755 "$SCRIPT_DIR/algol-init" "$TARGET_ROOT/usr/local/bin/algol-init"
install -m 0755 "$SCRIPT_DIR/pacman" "$TARGET_ROOT/usr/local/bin/pacman"

install -d "$TARGET_ROOT/etc/default"
if [[ -f "$TARGET_ROOT/etc/default/grub" ]]; then
    sed -i '/^[[:space:]]*GRUB_DISABLE_OS_PROBER=/d' \
        "$TARGET_ROOT/etc/default/grub"
fi
printf '%s\n' 'GRUB_DISABLE_OS_PROBER=true' \
    >> "$TARGET_ROOT/etc/default/grub"

install -d "$TARGET_ROOT/opt/alcor-installer"
for installer_file in alcor_frontend.py red_alcor.png blue_alcor.png purple_alcor.png expert_alcor.png; do
    if [[ ! -f "$SCRIPT_DIR/installer/$installer_file" ]]; then
        echo "[!] [Alcor] Installer file is missing: $installer_file" >&2
        exit 1
    fi
    install -m 0644 "$SCRIPT_DIR/installer/$installer_file" \
        "$TARGET_ROOT/opt/alcor-installer/$installer_file"
done
install -m 0755 "$SCRIPT_DIR/installer/alcor-installer" \
    "$TARGET_ROOT/usr/local/bin/alcor-installer"
install -m 0755 "$SCRIPT_DIR/installer/alcor-install" \
    "$TARGET_ROOT/usr/local/bin/alcor-install"
install -d "$TARGET_ROOT/etc/skel/Desktop"
install -m 0644 "$SCRIPT_DIR/installer/alcor-install.desktop" \
    "$TARGET_ROOT/etc/skel/Desktop/alcor-install.desktop"

printf '%s\n' "$KERNELS" > "$TARGET_ROOT/etc/alcor/kernels"

install -m 0755 "$SCRIPT_DIR/alcor-firstboot" \
    "$TARGET_ROOT/usr/local/sbin/alcor-firstboot"
install -m 0644 "$SCRIPT_DIR/alcor-firstboot.service" \
    "$TARGET_ROOT/etc/systemd/system/alcor-firstboot.service"
install -m 0644 "$SCRIPT_DIR/alcor-firstboot.timer" \
    "$TARGET_ROOT/etc/systemd/system/alcor-firstboot.timer"

rm -f "$TARGET_ROOT/etc/systemd/system/multi-user.target.wants/alcor-firstboot.service"
install -d "$TARGET_ROOT/etc/systemd/system/timers.target.wants"
ln -sfn /etc/systemd/system/alcor-firstboot.timer \
    "$TARGET_ROOT/etc/systemd/system/timers.target.wants/alcor-firstboot.timer"

while IFS=: read -r username _ uid gid _ home _; do
    if [[ "$uid" -ge 1000 && "$uid" -lt 60000 && "$username" != "nobody" && -d "$home" ]]; then
        TARGET_HOME="$TARGET_ROOT$home"
        install -d -o "$uid" -g "$gid" "$TARGET_HOME"
        if [[ ! -x "$TARGET_ROOT/usr/bin/zsh" ]]; then
            echo "[!] [Alcor] zsh was not installed; cannot set the default shell for $username." >&2
            exit 1
        fi
        if ! arch-chroot "$TARGET_ROOT" usermod --shell /usr/bin/zsh "$username"; then
            echo "[!] [Alcor] Failed to set zsh as the login shell for $username." >&2
            exit 1
        fi

        LIVE_HOME=""
        if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
            LIVE_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6 || true)"
        fi
        if [[ -z "$LIVE_HOME" || ! -d "$LIVE_HOME" ]]; then
            LIVE_HOME="/home/alcor"
        fi
        for config_file in .zshrc .zprofile .zshenv .bashrc .bash_profile .profile; do
            if [[ -f "$LIVE_HOME/$config_file" && ! -e "$TARGET_HOME/$config_file" ]]; then
                install -o "$uid" -g "$gid" -m 0644 \
                    "$LIVE_HOME/$config_file" "$TARGET_HOME/$config_file"
            fi
        done
        ZSHENV_FILE="$TARGET_HOME/.zshenv"
        if [[ ! -e "$ZSHENV_FILE" ]]; then
            install -o "$uid" -g "$gid" -m 0644 /dev/null "$ZSHENV_FILE"
        fi
        if ! grep -qF '# Alcor: add exported commands to PATH' "$ZSHENV_FILE"; then
            cat >> "$ZSHENV_FILE" <<'EOF'

# Alcor: add exported commands to PATH
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
EOF
            chown "$uid:$gid" "$ZSHENV_FILE"
        fi
        if [[ -d "$LIVE_HOME/.config/xfce4/terminal" ]]; then
            install -d -o "$uid" -g "$gid" "$TARGET_HOME/.config/xfce4"
            cp -an "$LIVE_HOME/.config/xfce4/terminal" \
                "$TARGET_HOME/.config/xfce4/"
            chown -R "$uid:$gid" "$TARGET_HOME/.config/xfce4/terminal"
        fi

        install -d -o "$uid" -g "$gid" "$TARGET_ROOT$home/Desktop"
        install -o "$uid" -g "$gid" -m 0644 \
            "$SCRIPT_DIR/installer/alcor-install.desktop" \
            "$TARGET_ROOT$home/Desktop/alcor-install.desktop"
    fi
done < "$TARGET_ROOT/etc/passwd"

echo "[+] [Alcor] Backend installed into $TARGET_ROOT"