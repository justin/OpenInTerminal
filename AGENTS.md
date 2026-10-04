# Repository Guidelines

## Project Structure & Module Organization

Open `OpenInTerminal.xcworkspace` for all apps.

- `OpenInTerminal/`: AppKit menu-bar app, preferences controllers, storyboards, and assets.
- `OpenInTerminalCore/`: shared preferences, application discovery, launch logic, and scripting bridges.
- `OpenInTerminalFinderExtension/`: sandboxed Finder Sync menus and actions.
- `OpenInTerminalHelper/`: embedded login helper.
- `OpenInTerminal-Lite/` and `OpenInEditor-Lite/`: standalone apps and Xcode projects.
- `Tests/`: executable Swift regression harnesses; `scripts/`: build and test entrypoints.
- `Resources/`: documentation and supplementary assets. Target-local `.xcassets` and `.lproj` directories contain icons and translations.

## Build, Test, and Development Commands

Use Xcode 27; the deployment target is macOS 13. Run `just` to list recipes.

- `just build`: build the full app in Debug.
- `just build Release OpenInTerminal-Lite`: select a configuration and scheme.
- `just run`: build and launch; `just run --verify` also checks the process starts.
- `just test`: build and run regression harnesses.
- `just build-signed`: export Developer ID-signed apps without notarization.
- `just build-unsigned`: export ad-hoc-signed apps.
- `just notarize`: build, sign, submit to Apple, and staple artifacts.

Outputs belong in ignored `build/` and `export/` directories.

## Coding Style & Naming Conventions

Use four-space Swift indentation, `UpperCamelCase` types, and `lowerCamelCase` methods and properties. Match surrounding conventions, including existing constants, import order, and `MARK` sections. Preserve useful comments and macOS 13 compatibility.

No Swift formatter or linter configuration is checked in. Use `just --fmt --check` for the Justfile, `bash -n` on each changed shell script, and `git diff --check`.

## Testing Guidelines

Tests use standalone Swift executables with `precondition` assertions, not XCTest or Swift Testing. Place focused harnesses under `Tests/<Behavior>/main.swift` and wire them into `scripts/test.sh`. Use temporary UserDefaults suites; never reset real preferences.

Add regression coverage for behavior changes. Build affected schemes, including both Lite apps for shared-core changes. Report interactive Finder, Automation, login, and older-OS checks separately from automated results; no coverage-percentage gate exists.

## Commit & Pull Request Guidelines

Follow `jww-git-workflow`. Fork commits use capitalized imperative subjects, such as “Organize scripts and add common Just recipes”; upstream history includes `feat:`/`fix:` prefixes. Prefer the fork convention and explain non-obvious rationale in the body.

Follow `.github/PULL_REQUEST_TEMPLATE.md`: summarize behavior, link relevant issues, provide test steps/results, and include screenshots for visible changes.

## Signing & Configuration

Keep `com.justinwme` identifiers and team `7B7LC48KU7` consistent across targets. The host and extension must share matching app-group entitlements; ad-hoc signing cannot authorize that group. Keep certificates and notarization credentials outside the repository.
