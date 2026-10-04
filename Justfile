# List available commands.
default:
    @just --list

# Build a configuration and scheme without launching.
build configuration="Debug" scheme="OpenInTerminal":
    xcodebuild -workspace OpenInTerminal.xcworkspace -scheme "{{ scheme }}" -configuration "{{ configuration }}" -derivedDataPath build -destination 'generic/platform=macOS' build

# Build and launch; optional modes: --debug, --logs, --verify.
run mode="run":
    ./scripts/build_and_run.sh "{{ mode }}"

# Run the isolated regression checks.
test:
    ./scripts/test.sh

# Export Developer ID-signed apps and ZIPs without notarization.
build-signed:
    SKIP_NOTARIZE=1 ./scripts/build-signed.sh

# Export ad-hoc-signed apps (shared app group requires team signing).
build-unsigned:
    ./scripts/build-unsigned.sh

# Build, sign, submit to Apple for notarization, and staple all apps.
notarize:
    SKIP_NOTARIZE=0 ./scripts/build-signed.sh
