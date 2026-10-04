# List available commands.
default:
    @just --list

# Build OpenInTerminal without launching.
build configuration="Debug":
    xcodebuild -workspace OpenInTerminal.xcworkspace -scheme OpenInTerminal -configuration "{{ configuration }}" -derivedDataPath build -destination 'generic/platform=macOS' build

# Build and launch; optional modes: --debug, --logs, --verify.
run mode="run":
    ./scripts/build_and_run.sh "{{ mode }}"

# Run the isolated regression checks.
test:
    ./scripts/test.sh

# Export Developer ID-signed app and ZIP without notarization.
build-signed:
    SKIP_NOTARIZE=1 ./scripts/build-signed.sh

# Export an ad-hoc-signed app (shared app group requires team signing).
build-unsigned:
    ./scripts/build-unsigned.sh

# Build, sign, submit to Apple for notarization, and staple OpenInTerminal.
notarize:
    SKIP_NOTARIZE=0 ./scripts/build-signed.sh
