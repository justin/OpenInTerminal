#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-run}"
case "$MODE" in
  run|--debug|--logs|--verify) ;;
  *) echo "usage: $0 [--debug|--logs|--verify]" >&2; exit 2 ;;
esac
cd "$ROOT_DIR"
APP="$ROOT_DIR/build/Build/Products/Debug/OpenInTerminal.app"
# Stop only this checkout's build, leaving installed copies alone.
pkill -f "^$APP/Contents/MacOS/OpenInTerminal$" >/dev/null 2>&1 || true
xcodebuild -workspace OpenInTerminal.xcworkspace -scheme OpenInTerminal \
  -configuration Debug -derivedDataPath build -destination 'generic/platform=macOS' build
case "$MODE" in
  --debug) exec lldb -- "$APP/Contents/MacOS/OpenInTerminal" ;;
  --logs)
    open -n "$APP"
    exec /usr/bin/log stream --info --style compact --predicate 'process == "OpenInTerminal"'
    ;;
  --verify)
    open -n "$APP"
    sleep 2
    pgrep -f "^$APP/Contents/MacOS/OpenInTerminal$" >/dev/null
    ;;
  run) open -n "$APP" ;;
esac
