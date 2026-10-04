#!/usr/bin/env python3
"""Publish a notarized release and update Justin's Homebrew cask."""

import argparse
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "justin/OpenInTerminal"
TAP = "justin/tap"
PROJECT = Path("OpenInTerminal.xcodeproj/project.pbxproj")
ASSET = "OpenInTerminal.zip"


def run(*args, cwd=ROOT, capture=False, env=None):
    result = subprocess.run(args, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, env=env)
    return result.stdout.strip() if capture else None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def version_number(value):
    require(re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value),
            "Version must be X.Y.Z or vX.Y.Z, without a prerelease suffix.")
    return tuple(map(int, value.split(".")))


def project_versions(text):
    versions = re.findall(r"MARKETING_VERSION = ([0-9.]+);", text)
    builds = re.findall(r"CURRENT_PROJECT_VERSION = ([0-9]+);", text)
    require(len(versions) == len(builds) == 8,
            "Expected version and integer build settings for all four targets in Debug/Release.")
    return versions, builds


def bump_version(text, version):
    versions, builds = project_versions(text)
    require(version_number(version) > max(map(version_number, versions)),
            "Release version must be newer than every current target version.")
    build = str(max(map(int, builds)) + 1)
    text = re.sub(r"MARKETING_VERSION = [0-9.]+;", f"MARKETING_VERSION = {version};", text)
    text = re.sub(r"CURRENT_PROJECT_VERSION = [0-9]+;", f"CURRENT_PROJECT_VERSION = {build};", text)
    return text, build


def verify_app(app, version, build):
    # Check the distributed host, extension, helper, and shared framework.
    plists = [app / "Contents/Info.plist"]
    for pattern in ("**/*.appex/Contents/Info.plist", "**/*.app/Contents/Info.plist",
                    "**/*.framework/Resources/Info.plist"):
        plists.extend(app.glob(pattern))
    require(len(plists) >= 4, "Export is missing an embedded bundle.")
    for path in plists:
        with path.open("rb") as source:
            info = plistlib.load(source)
        require(info["CFBundleShortVersionString"] == version and info["CFBundleVersion"] == build,
                f"Incorrect version/build in {path}")
    run("codesign", "--verify", "--deep", "--strict", str(app))
    run("xcrun", "stapler", "validate", str(app))
    run("spctl", "-a", "-t", "exec", "-vv", str(app))


def cask_text(version, checksum):
    return f'''cask "openinterminal" do
  version "{version}"
  sha256 "{checksum}"

  url "https://github.com/{REPO}/releases/download/v#{{version}}/{ASSET}"
  name "OpenInTerminal"
  desc "Open terminals and editors from Finder"
  homepage "https://github.com/{REPO}"

  depends_on macos: :sonoma

  app "OpenInTerminal.app"
end
'''


def release(version, resume):
    version_number(version)
    tag = f"v{version}"
    require(not run("git", "status", "--porcelain", capture=True), "Commit or stash changes first.")
    require(run("git", "branch", "--show-current", capture=True) == "master",
            "Release from master.")
    remote = run("git", "remote", "get-url", "--push", "origin", capture=True)
    require(remote in (f"git@github.com:{REPO}.git", f"https://github.com/{REPO}.git"),
            f"origin must point to {REPO}.")
    run("gh", "auth", "status")
    run("git", "fetch", "origin", "master")
    run("git", "merge-base", "--is-ancestor", "origin/master", "HEAD")
    local_tag = run("git", "tag", "--list", tag, capture=True)
    remote_tag = run("git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}", capture=True)
    text = (ROOT / PROJECT).read_text()
    if resume:
        versions, builds = project_versions(text)
        require(set(versions) == {version} and len(set(builds)) == 1,
                "Resume requires the release version and build in every target.")
        require(run("git", "log", "-1", "--format=%s", capture=True) == f"Release {tag}",
                "Resume requires the release commit at HEAD.")
        build = builds[0]
        if local_tag:
            require(run("git", "rev-parse", f"{tag}^{{commit}}", capture=True) ==
                    run("git", "rev-parse", "HEAD", capture=True), "Release tag must point to HEAD.")
        require(not remote_tag or (local_tag and remote_tag.split()[0] ==
                run("git", "rev-parse", f"refs/tags/{tag}", capture=True)),
                "Remote tag differs from the local tag.")
    else:
        require(not local_tag and not remote_tag, "Tag already exists; use --resume only for this release.")
        text, build = bump_version(text, version)

    # Listing failures must stop the release, never be mistaken for a missing release.
    pages = run("gh", "api", "--paginate", "--slurp", f"repos/{REPO}/releases", capture=True)
    existing = next((item for page in json.loads(pages) for item in page if item["tag_name"] == tag), None)
    require(not existing or resume, "GitHub release already exists.")
    require(not existing or (local_tag and remote_tag),
            "A published release requires matching local and remote tags.")
    require(not existing or (not existing["draft"] and not existing["prerelease"]),
            "An unfinished draft/prerelease exists. Inspect it on GitHub before resuming.")

    with tempfile.TemporaryDirectory(prefix="oit-release-") as temporary:
        temporary = Path(temporary)
        tap = temporary / "tap"
        run("gh", "repo", "clone", TAP, str(tap))
        if not resume:
            (ROOT / PROJECT).write_text(text)
            run("git", "add", str(PROJECT))
            run("git", "commit", "-S", "-m", f"Release {tag}")
        if not local_tag:
            run("git", "tag", "-s", tag, "-m", f"OpenInTerminal {tag}")
        release_commit = run("git", "rev-parse", "HEAD", capture=True)

        if not existing:
            run("bash", "scripts/build-signed.sh", env={**os.environ, "SKIP_NOTARIZE": "0"})
            verify_app(ROOT / "export/OpenInTerminal.app", version, build)
            require(not run("git", "status", "--porcelain", capture=True),
                    "Working tree changed during the build; refusing to publish.")
            require(run("git", "rev-parse", "HEAD", capture=True) == release_commit and
                    run("git", "rev-parse", f"{tag}^{{commit}}", capture=True) == release_commit,
                    "HEAD or the release tag changed during the build; refusing to publish.")
            # Publish the branch and exact tag together, only after notarization succeeds.
            run("git", "push", "--atomic", "origin", f"{release_commit}:refs/heads/master", f"refs/tags/{tag}")
            run("gh", "release", "create", tag, str(ROOT / "export" / ASSET), "--repo", REPO,
                "--verify-tag", "--title", f"OpenInTerminal {tag}", "--generate-notes", "--latest")

        downloaded = temporary / "download"
        run("gh", "release", "download", tag, "--repo", REPO, "--pattern", ASSET, "--dir", str(downloaded))
        archive = downloaded / ASSET
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        if not existing:
            require(checksum == hashlib.sha256((ROOT / "export" / ASSET).read_bytes()).hexdigest(),
                    "Downloaded release checksum differs from the notarized export.")
        unpacked = temporary / "unpacked"
        run("ditto", "-x", "-k", str(archive), str(unpacked))
        verify_app(unpacked / "OpenInTerminal.app", version, build)
        cask = tap / "Casks/openinterminal.rb"
        cask.parent.mkdir(exist_ok=True)
        if cask.exists():
            contents = cask.read_text()
            require(f"https://github.com/{REPO}/releases/download/" in contents,
                    "Existing cask does not point to this fork.")
            current = re.search(r'^  version "([0-9.]+)"$', contents, re.MULTILINE)
            require(current and version_number(current[1]) <= version_number(version),
                    "Refusing to downgrade the tap.")
            for key, value in (("version", version), ("sha256", checksum)):
                contents, count = re.subn(rf'^  {key} "[^"\n]+"$', f'  {key} "{value}"',
                                          contents, flags=re.MULTILINE)
                require(count == 1, f"Expected one {key} field in the cask.")
        else:
            contents = cask_text(version, checksum)
        cask.write_text(contents)
        run("brew", "style", str(cask), cwd=tap)
        if run("git", "status", "--porcelain", capture=True, cwd=tap):
            run("git", "add", "Casks/openinterminal.rb", cwd=tap)
            run("git", "commit", "-S", "-m", f"Update OpenInTerminal to {version}", cwd=tap)
            run("git", "push", "origin", "HEAD", cwd=tap)
    print(f"Released https://github.com/{REPO}/releases/tag/{tag}")
    print("Install with: brew install --cask justin/tap/openinterminal")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="X.Y.Z or vX.Y.Z")
    parser.add_argument("--resume", action="store_true", help="Resume at the existing release commit")
    args = parser.parse_args()
    try:
        release(args.version.removeprefix("v"), args.resume)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Release stopped: {error}", file=sys.stderr)
        print("No automatic rollback was performed. Inspect Git status and GitHub; after fixing the\n"
              "failure, use --resume if the release commit exists. Never move a published tag.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
