#!/usr/bin/env bash
# Harness Designer — macOS package builder
# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Produces a signed (or unsigned) .pkg installer using Apple's native
# pkgbuild + productbuild tools (included with Xcode Command Line Tools).
#
# Prerequisites:
#   - Xcode Command Line Tools: xcode-select --install
#   - Build the app:            python -m builder  (produces builder/scripts/dist/harness_designer.app)
#   - Build the installer:      build_dependency_installer() (produces builder/scripts/dist/dep_installer)
#
# Optional (for signing and notarization):
#   - Apple Developer ID: set DEVELOPER_ID_APP and DEVELOPER_ID_INSTALLER below
#   - xcrun notarytool credentials configured
#
# Usage:
#   chmod +x build_pkg.sh
#   ./build_pkg.sh [--version 1.0.0] [--sign]

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

APP_NAME="HarnessDesigner"
APP_DISPLAY_NAME="Harness Designer"
APP_VERSION="1.0.0"
BUNDLE_ID="com.kevinschlosser.harnessdesigner"
SIGN=""   # set to non-empty (e.g. 1) only when --sign is passed

# Code signing identities (only used when --sign is passed)
DEVELOPER_ID_APP="Developer ID Application: Kevin G. Schlosser (TEAMID)"
DEVELOPER_ID_INSTALLER="Developer ID Installer: Kevin G. Schlosser (TEAMID)"

# ── Argument parsing ─────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version) APP_VERSION="$2"; shift 2 ;;
        --sign)    SIGN=1;           shift   ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/builder/scripts/dist"
WORK_DIR="$SCRIPT_DIR/work"
OUTPUT_DIR="$REPO_ROOT/dist/macos"

APP_SRC="$BUILD_DIR/harness_designer.app"
INSTALLER_SRC="$BUILD_DIR/dep_installer"
PAYLOAD_DIR="$WORK_DIR/payload"
INSTALL_APP="$PAYLOAD_DIR/Applications/$APP_NAME.app"
COMPONENT_PKG="$WORK_DIR/$APP_NAME-component.pkg"
FINAL_PKG="$OUTPUT_DIR/${APP_NAME}-${APP_VERSION}.pkg"

# ── Preflight checks ─────────────────────────────────────────────────────────

echo "→ Checking prerequisites..."

for tool in pkgbuild productbuild; do
    if ! command -v "$tool" &>/dev/null; then
        echo "Error: $tool not found. Install Xcode Command Line Tools: xcode-select --install"
        exit 1
    fi
done

if [[ ! -d "$APP_SRC" ]]; then
    echo "Error: App not built. Expected: $APP_SRC"
    exit 1
fi

if [[ ! -f "$INSTALLER_SRC" ]]; then
    echo "Error: Dependency installer not built. Expected: $INSTALLER_SRC"
    exit 1
fi

# ── Assemble payload ─────────────────────────────────────────────────────────

echo "→ Assembling payload..."

rm -rf "$WORK_DIR"
mkdir -p "$PAYLOAD_DIR/Applications"
mkdir -p "$OUTPUT_DIR"

# Copy the main app bundle
cp -R "$APP_SRC" "$INSTALL_APP"

# Embed the dependency installer inside the app bundle so the postinstall
# script can find and run it without needing a separate extraction step.
RESOURCES_DIR="$INSTALL_APP/Contents/Resources"
mkdir -p "$RESOURCES_DIR"
cp "$INSTALLER_SRC" "$RESOURCES_DIR/dep_installer"
chmod +x "$RESOURCES_DIR/dep_installer"

# ── Code sign the app (optional) ─────────────────────────────────────────────

if [[ -n "$SIGN" ]]; then
    echo "→ Signing app bundle..."
    codesign --deep --force --verify --verbose \
        --sign "$DEVELOPER_ID_APP" \
        --options runtime \
        "$INSTALL_APP"
fi

# ── Build component package ───────────────────────────────────────────────────

echo "→ Building component package..."

SCRIPTS_DIR="$SCRIPT_DIR/scripts"

pkgbuild \
    --root "$PAYLOAD_DIR" \
    --identifier "$BUNDLE_ID" \
    --version "$APP_VERSION" \
    --install-location "/" \
    --scripts "$SCRIPTS_DIR" \
    "$COMPONENT_PKG"

# ── Stage resources with the PySide6/Qt LGPLv3 notice inlined ────────────────
# license.html has placeholder comments for the LGPLv3/GPLv3 text and
# PySide6's own bundled commercial-reference notice (see
# harness_designer/licenses/ and harness_designer/ui/dialogs/about_dialog.py
# for the same text shown post-install) -- inline the real files into a
# staged copy rather than editing the committed template.

echo "→ Staging installer resources with third-party license text inlined..."

RESOURCES_WORK_DIR="$WORK_DIR/resources"
rm -rf "$RESOURCES_WORK_DIR"
cp -R "$SCRIPT_DIR/resources" "$RESOURCES_WORK_DIR"

python3 - "$REPO_ROOT/harness_designer/licenses" "$RESOURCES_WORK_DIR/license.html" <<'PYEOF'
import html
import pathlib
import sys

licenses_dir, license_html = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])

replacements = {
    'pyside6-lgplv3': 'LGPLv3.txt',
    'pyside6-gplv3': 'GPLv3.txt',
    'pyside6-commercial-ref': 'Qt-Commercial-Reference.txt',
}

text = license_html.read_text(encoding='utf-8')
for element_id, filename in replacements.items():
    marker_open = f'id="{element_id}">'
    start = text.index(marker_open) + len(marker_open)
    end = text.index('</pre>', start)
    body = html.escape((licenses_dir / filename).read_text(encoding='utf-8'))
    text = text[:start] + '\n' + body + text[end:]

license_html.write_text(text, encoding='utf-8')
PYEOF

# ── Build distribution package ────────────────────────────────────────────────

echo "→ Building distribution package..."

productbuild \
    --distribution "$SCRIPT_DIR/distribution.xml" \
    --package-path "$WORK_DIR" \
    --resources "$RESOURCES_WORK_DIR" \
    ${SIGN:+--sign "$DEVELOPER_ID_INSTALLER"} \
    "$FINAL_PKG"

# ── Notarize (optional, requires --sign and configured credentials) ───────────

if [[ -n "$SIGN" ]]; then
    echo "→ Submitting for notarization..."
    xcrun notarytool submit "$FINAL_PKG" \
        --keychain-profile "AC_PASSWORD" \
        --wait
    xcrun stapler staple "$FINAL_PKG"
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────

rm -rf "$WORK_DIR"

echo ""
echo "✓ Package built: $FINAL_PKG"
