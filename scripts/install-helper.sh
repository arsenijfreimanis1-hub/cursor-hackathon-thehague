#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HELPER_DIR="$ROOT/macos-helper"
APP_DIR="$HELPER_DIR/JarvisHelper.app"
BINARY="$HELPER_DIR/.build/release/JarvisHelper"

cd "$HELPER_DIR"
swift build -c release

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cp "$BINARY" "$APP_DIR/Contents/MacOS/JarvisHelper"
chmod +x "$APP_DIR/Contents/MacOS/JarvisHelper"

cat > "$APP_DIR/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>JarvisHelper</string>
  <key>CFBundleIdentifier</key>
  <string>com.willy.jarvis-helper</string>
  <key>CFBundleName</key>
  <string>JarvisHelper</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
EOF

PLIST_DST="$HOME/Library/LaunchAgents/com.willy.jarvis-helper.plist"
cat > "$PLIST_DST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.willy.jarvis-helper</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProgramArguments</key>
    <array>
      <string>$APP_DIR/Contents/MacOS/JarvisHelper</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HELPER_DIR</string>
    <key>StandardOutPath</key>
    <string>$ROOT/logs/helper.log</string>
    <key>StandardErrorPath</key>
    <string>$ROOT/logs/helper.err.log</string>
  </dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/com.willy.jarvis-helper" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.willy.jarvis-helper"
launchctl kickstart -k "gui/$(id -u)/com.willy.jarvis-helper"

echo "macOS helper running on http://127.0.0.1:8788"
