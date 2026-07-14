#!/usr/bin/env bash
# Build a Linux AppImage for the Dracula Adventure GUI.
# Prereq: PyInstaller has produced dist/dracula and dist/dracula-gui (onefile).
# Usage:  installer/linux/build-appimage.sh <version>
set -euo pipefail

VERSION="${1:?usage: build-appimage.sh <version>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$ROOT/dist/Dracula.AppDir"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" \
         "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/512x512/apps"

install -m755 "$ROOT/dist/dracula-gui" "$APPDIR/usr/bin/dracula-gui"
install -m755 "$ROOT/dist/dracula"     "$APPDIR/usr/bin/dracula"

# .desktop + icon, both at AppDir root (required by AppImage) and in the usual paths.
install -m644 "$ROOT/installer/linux/dracula.desktop" "$APPDIR/usr/share/applications/dracula-adventure.desktop"
install -m644 "$ROOT/installer/linux/dracula.desktop" "$APPDIR/dracula-adventure.desktop"
install -m644 "$ROOT/icon/vampire.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/dracula-adventure.png"
install -m644 "$ROOT/icon/vampire.png" "$APPDIR/dracula-adventure.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/dracula-gui" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Fetch appimagetool (itself an AppImage). CI runners lack FUSE, so run it with
# --appimage-extract-and-run.
TOOL="$ROOT/dist/appimagetool-x86_64.AppImage"
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi

OUT="$ROOT/dist/Dracula-Adventure-${VERSION}-x86_64.AppImage"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"
echo "built: $OUT"
