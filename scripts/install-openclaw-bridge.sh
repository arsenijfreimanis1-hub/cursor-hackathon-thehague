#!/usr/bin/env bash
set -euo pipefail

BRIDGE_DIR="/Users/willy/jarvis-core/openclaw-bridge"

openclaw plugins install --link "$BRIDGE_DIR"

openclaw config patch --stdin <<'EOF'
{
  "plugins": {
    "entries": {
      "jarvis-bridge": {
        "enabled": true,
        "config": {
          "jarvisUrl": "http://127.0.0.1:8787",
          "channels": ["whatsapp"]
        }
      }
    }
  }
}
EOF

launchctl kickstart -k "gui/$(id -u)/ai.openclaw.gateway" 2>/dev/null || true

echo "OpenClaw bridge installed. WhatsApp messages now route to JarvisCore."
