#!/usr/bin/env bash
# Harness Designer — Linux installer
# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Supports Debian/Ubuntu, Fedora/RHEL/CentOS, Arch, and any distro
# with a standard FHS layout.
#
# Usage:
#   chmod +x install.sh
#   sudo ./install.sh [--prefix /opt]   (system-wide, requires sudo)
#         ./install.sh --user           (current user only, no sudo needed)
#         ./install.sh --uninstall      (removes a previous installation)

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────

APP_NAME="harness_designer"
APP_DISPLAY_NAME="Harness Designer"
APP_VERSION="1.0.0"
ICON_NAME="harness_designer"

# ── Defaults ──────────────────────────────────────────────────────────────────

INSTALL_MODE="system"   # system | user
UNINSTALL=0
PREFIX=""               # overridden by --prefix

# ── Argument parsing ──────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)         INSTALL_MODE="user";   shift   ;;
        --prefix)       PREFIX="$2";           shift 2 ;;
        --uninstall)    UNINSTALL=1;           shift   ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Resolve install paths ─────────────────────────────────────────────────────

if [[ "$INSTALL_MODE" == "user" ]]; then
    PREFIX="${PREFIX:-$HOME/.local}"
    DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
    BIN_DIR="$HOME/.local/bin"
    NEED_SUDO=0
else
    PREFIX="${PREFIX:-/opt/$APP_NAME}"
    DESKTOP_DIR="/usr/share/applications"
    ICON_DIR="/usr/share/icons/hicolor/256x256/apps"
    BIN_DIR="/usr/local/bin"
    NEED_SUDO=1
fi

APP_DIR="$PREFIX/$APP_NAME"
LIB_DIR="$APP_DIR"

# ── Sudo wrapper ──────────────────────────────────────────────────────────────

run() {
    if [[ $NEED_SUDO -eq 1 && $EUID -ne 0 ]]; then
        sudo "$@"
    else
        "$@"
    fi
}

# ── Uninstall ─────────────────────────────────────────────────────────────────

if [[ $UNINSTALL -eq 1 ]]; then
    echo "Uninstalling $APP_DISPLAY_NAME..."
    run rm -rf "$APP_DIR"
    run rm -f  "$BIN_DIR/$APP_NAME"
    run rm -f  "$DESKTOP_DIR/$APP_NAME.desktop"
    run rm -f  "$ICON_DIR/$ICON_NAME.png"
    if command -v update-desktop-database &>/dev/null; then
        run update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        run gtk-update-icon-cache -f -t "$(dirname "$ICON_DIR")" 2>/dev/null || true
    fi
    echo "Uninstall complete."
    exit 0
fi

# ── Locate build output ───────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/builder/scripts/dist"
APP_SRC="$BUILD_DIR/$APP_NAME"
INSTALLER_SRC="$BUILD_DIR/installer"
ICON_SRC="$REPO_ROOT/harness_designer/image/icon_256x256.png"

for path in "$APP_SRC" "$INSTALLER_SRC" "$ICON_SRC"; do
    if [[ ! -e "$path" ]]; then
        echo "Error: expected build output not found: $path"
        echo "Run the builder first: python -m builder"
        exit 1
    fi
done

# ── Install files ─────────────────────────────────────────────────────────────

echo "Installing $APP_DISPLAY_NAME ${APP_VERSION}..."
echo "  Destination: $APP_DIR"
echo ""

run mkdir -p "$APP_DIR"
run mkdir -p "$BIN_DIR"
run mkdir -p "$DESKTOP_DIR"
run mkdir -p "$ICON_DIR"

echo "Copying application files..."
run cp -r "$APP_SRC/." "$APP_DIR/"
run chmod +x "$APP_DIR/$APP_NAME"

echo "Installing icon..."
run cp "$ICON_SRC" "$ICON_DIR/$ICON_NAME.png"

echo "Creating launcher symlink..."
run ln -sf "$APP_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"

echo "Creating desktop entry..."
run tee "$DESKTOP_DIR/$APP_NAME.desktop" > /dev/null <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_DISPLAY_NAME
GenericName=Electrical Harness Designer
Comment=Design and document electrical harnesses
Exec=$APP_DIR/$APP_NAME %F
Icon=$ICON_NAME
Terminal=false
Categories=Engineering;Electronics;
MimeType=application/x-harness-designer;
StartupNotify=true
EOF

if command -v update-desktop-database &>/dev/null; then
    run update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    run gtk-update-icon-cache -f -t "$(dirname "$ICON_DIR")" 2>/dev/null || true
fi

# ── Install dependencies ──────────────────────────────────────────────────────

echo "Installing required Python components..."
echo "  A component selection window will appear."
echo ""

INSTALLER_TMP="$(mktemp)"
cp "$INSTALLER_SRC" "$INSTALLER_TMP"
chmod +x "$INSTALLER_TMP"

# Run as the current user (not root) so the GUI appears correctly.
# If we are root (sudo), drop back to the original user.
if [[ $NEED_SUDO -eq 1 && -n "${SUDO_USER:-}" ]]; then
    run mkdir -p "$LIB_DIR"
    run chown "$SUDO_USER:$(id -gn "$SUDO_USER")" "$LIB_DIR"
    sudo -u "$SUDO_USER" "$INSTALLER_TMP" "$LIB_DIR"
else
    mkdir -p "$LIB_DIR"
    "$INSTALLER_TMP" "$LIB_DIR"
fi

rm -f "$INSTALLER_TMP"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "$APP_DISPLAY_NAME ${APP_VERSION} installed successfully."
echo ""
if [[ "$INSTALL_MODE" == "user" && ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "  Note: $BIN_DIR is not in your PATH."
    echo "  Add this to your shell profile (~/.bashrc or ~/.zshrc):"
    echo "    export PATH=\"\$PATH:$BIN_DIR\""
    echo ""
fi
echo "  Launch: $APP_NAME"
echo "  Or find '$APP_DISPLAY_NAME' in your application menu."
