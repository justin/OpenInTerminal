#!/usr/bin/env python3
"""Update all target versions and build numbers, then commit and tag the release."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = Path("OpenInTerminal.xcodeproj/project.pbxproj")


def git(*args):
    return subprocess.run(("git", *args), cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


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


def release(version):
    version_number(version)
    tag = f"v{version}"
    require(not git("status", "--porcelain"), "Commit or stash changes first.")
    require(not git("tag", "--list", tag), f"Tag {tag} already exists.")
    project = ROOT / PROJECT
    text, build = bump_version(project.read_text(), version)
    project.write_text(text)
    git("add", str(PROJECT))
    git("commit", "-m", f"Release {tag}")
    git("tag", "-a", tag, "-m", f"OpenInTerminal {tag}")
    print(f"Committed and tagged {tag} (build {build}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="X.Y.Z or vX.Y.Z")
    args = parser.parse_args()
    try:
        release(args.version.removeprefix("v"))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Release preparation failed: {error}", file=sys.stderr)
        print("Inspect Git status, the latest commit, and tags before retrying; "
              "no automatic rollback was performed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
