#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
python3 -B Tests/Release/test_release.py
xcodebuild -project OpenInTerminal.xcodeproj -scheme OpenInTerminal \
  -configuration Debug -derivedDataPath build -destination 'generic/platform=macOS' build
PRODUCTS="$ROOT_DIR/build/Build/Products/Debug"
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/oit-finder-tests.XXXXXX")"
trap 'rm -rf "$TEST_DIR"' EXIT
xcrun swiftc -F "$PRODUCTS" -framework OpenInTerminalCore -framework FinderSync \
  -Xlinker -rpath -Xlinker "$PRODUCTS" \
  OpenInTerminalFinderExtension/FinderSync.swift Tests/FinderMenu/main.swift \
  -o "$TEST_DIR/FinderMenuTests"
"$TEST_DIR/FinderMenuTests"

# Compile the app classes without starting NSApplicationMain or loading its UI.
sed '/^@NSApplicationMain$/d' OpenInTerminal/AppDelegate.swift > "$TEST_DIR/AppDelegate.swift"
APP_SOURCES=()
while IFS= read -r -d '' source; do
  APP_SOURCES+=("$source")
done < <(find OpenInTerminal -name '*.swift' ! -name AppDelegate.swift -print0)
xcrun swiftc -F "$PRODUCTS" -framework OpenInTerminalCore -framework Carbon \
  -I "$ROOT_DIR/build/SourcePackages/checkouts/ShortcutRecorder/Sources/ShortcutRecorder/include" \
  -Xcc "-fmodule-map-file=$ROOT_DIR/build/Build/Intermediates.noindex/GeneratedModuleMaps/ShortcutRecorder.modulemap" \
  -Xlinker -rpath -Xlinker "$PRODUCTS" \
  "${APP_SOURCES[@]}" "$TEST_DIR/AppDelegate.swift" Tests/Shortcuts/main.swift \
  "$PRODUCTS/ShortcutRecorder.o" -o "$TEST_DIR/ShortcutTests"
"$TEST_DIR/ShortcutTests"
