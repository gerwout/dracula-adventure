#!/usr/bin/env bash
# Build a macOS .dmg for Dracula Adventure.
# Prereq: PyInstaller has produced "dist/Dracula Adventure.app" (windowed BUNDLE)
#         and dist/dracula (CLI binary). Run on a macOS runner.
# Usage:  installer/macos/build-dmg.sh <version>
set -euo pipefail

VERSION="${1:?usage: build-dmg.sh <version>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/dist/Dracula Adventure.app"
STAGE="$ROOT/dist/dmg"

# 1. Generate a proper .icns from the PNG and inject it into the .app.
ICONSET="$ROOT/dist/dracula.iconset"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512; do
  sips -z "$size" "$size"      "$ROOT/icon/vampire.png" --out "$ICONSET/icon_${size}x${size}.png"   >/dev/null
  sips -z $((size*2)) $((size*2)) "$ROOT/icon/vampire.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$APP/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" "$APP/Contents/Info.plist"

# 2. Stage the .dmg contents: the app, the CLI binary, a link to /Applications, docs.
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
install -m755 "$ROOT/dist/dracula" "$STAGE/dracula"
cp "$ROOT/README.md" "$STAGE/README.md"
ln -s /Applications "$STAGE/Applications"

# 3. Build the compressed .dmg.
OUT="$ROOT/dist/Dracula-Adventure-${VERSION}.dmg"
rm -f "$OUT"
hdiutil create -volname "Dracula Adventure" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
echo "built: $OUT"
