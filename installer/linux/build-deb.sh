#!/usr/bin/env bash
# Build a Debian/Ubuntu .deb package for Dracula Adventure.
# Prereq: PyInstaller has produced dist/dracula and dist/dracula-gui (onefile).
# Usage:  installer/linux/build-deb.sh <version>
set -euo pipefail

VERSION="${1:?usage: build-deb.sh <version>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG="$ROOT/dist/deb/dracula-adventure_${VERSION}_amd64"

rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" \
         "$PKG/usr/bin" \
         "$PKG/usr/share/applications" \
         "$PKG/usr/share/icons/hicolor/512x512/apps" \
         "$PKG/usr/share/doc/dracula-adventure"

install -m755 "$ROOT/dist/dracula"     "$PKG/usr/bin/dracula"
install -m755 "$ROOT/dist/dracula-gui" "$PKG/usr/bin/dracula-gui"
install -m644 "$ROOT/installer/linux/dracula.desktop" "$PKG/usr/share/applications/dracula-adventure.desktop"
install -m644 "$ROOT/icon/vampire.png" "$PKG/usr/share/icons/hicolor/512x512/apps/dracula-adventure.png"
install -m644 "$ROOT/LICENSE"          "$PKG/usr/share/doc/dracula-adventure/copyright"

cat > "$PKG/DEBIAN/control" <<EOF
Package: dracula-adventure
Version: ${VERSION}
Section: games
Priority: optional
Architecture: amd64
Maintainer: Gerwout van der Veen <gerwoutvdveen@gmail.com>
Depends: libc6
Description: Faithful Python port of the 1982 text adventure Dracula Avontuur
 A modern, self-contained reimplementation of the 1982 Dutch MS-DOS text
 adventure Dracula Avontuur. Provides a terminal version ("dracula") and a
 desktop GUI ("dracula-gui"). No original game files are needed to play.
EOF

dpkg-deb --root-owner-group --build "$PKG" "$ROOT/dist/dracula-adventure_${VERSION}_amd64.deb"
echo "built: $ROOT/dist/dracula-adventure_${VERSION}_amd64.deb"
