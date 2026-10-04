"""Exercise release ordering and failure boundaries without external side effects."""

import importlib.util
import json
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
VERIFY_APP = release.verify_app


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / release.PROJECT
        self.project.parent.mkdir()
        self.original = (ROOT / release.PROJECT).read_text()
        self.project.write_text(self.original)
        self.commands = []
        self.existing = False
        self.fail_build = False
        self.dirty = False
        self.change_head = False
        self.build_ran = False
        self.bad_download = False
        self.environment = None
        root_patch = patch.object(release, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        command_patch = patch.object(release, "run", side_effect=self.run_command)
        command_patch.start()
        self.addCleanup(command_patch.stop)
        verify_patch = patch.object(release, "verify_app")
        self.verify = verify_patch.start()
        self.addCleanup(verify_patch.stop)

    def run_command(self, *args, **kwargs):
        self.commands.append(args)
        if args[:3] == ("git", "status", "--porcelain"):
            return " M file" if self.dirty or "cwd" in kwargs else ""
        if args[:3] == ("git", "branch", "--show-current"):
            return "master"
        if args[:3] == ("git", "remote", "get-url"):
            return "git@github.com:justin/OpenInTerminal.git"
        if args[:3] == ("git", "tag", "--list"):
            return "v3.0.0" if self.existing else ""
        if args[:3] == ("git", "ls-remote", "--tags"):
            return "taghash\trefs/tags/v3.0.0" if self.existing else ""
        if args[:3] == ("git", "log", "-1"):
            return "Release v3.0.0"
        if args[:2] == ("git", "rev-parse"):
            if args[2] == "refs/tags/v3.0.0":
                return "taghash"
            return "changed" if self.change_head and self.build_ran else "releasehash"
        if args[:2] == ("gh", "api"):
            return json.dumps([[{"tag_name": "v3.0.0", "draft": False, "prerelease": False}]
                               if self.existing else []])
        if args[:3] == ("gh", "repo", "clone"):
            Path(args[4]).mkdir()
        if args[:2] == ("bash", "scripts/build-signed.sh"):
            self.environment = kwargs["env"]
            self.build_ran = True
            if self.fail_build:
                raise subprocess.CalledProcessError(1, args)
            (self.root / "export").mkdir()
            (self.root / "export" / release.ASSET).write_bytes(b"notarized archive")
        if args[:3] == ("gh", "release", "download"):
            destination = Path(args[-1])
            destination.mkdir()
            (destination / release.ASSET).write_bytes(b"bad" if self.bad_download else b"notarized archive")
        return ""

    def test_bumps_all_targets_once(self):
        updated, build = release.bump_version(self.original, "3.0.0")
        old_builds = release.project_versions(self.original)[1]
        self.assertEqual(int(build), max(map(int, old_builds)) + 1)
        self.assertEqual(release.project_versions(updated), (["3.0.0"] * 8, [build] * 8))

    def test_rejects_invalid_or_nonincreasing_versions(self):
        for version in ("2.4.0", "2.3.0", "3.0", "3.0.0-rc1", "03.0.0", "$(touch bad)"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.bump_version(self.original, version)

    def test_success_orders_commit_tag_build_publish_tap(self):
        release.release("3.0.0", False)
        def index(prefix):
            return next(i for i, command in enumerate(self.commands) if command[:len(prefix)] == prefix)
        indices = [index(prefix) for prefix in (
            ("git", "commit"), ("git", "tag", "-s"), ("bash",),
            ("git", "push", "--atomic"), ("gh", "release", "create"),
            ("gh", "release", "download"), ("brew", "style"), ("git", "push", "origin"))]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(self.environment["SKIP_NOTARIZE"], "0")
        self.assertEqual(self.verify.call_count, 2)

    def test_failed_build_never_publishes(self):
        self.fail_build = True
        with self.assertRaises(subprocess.CalledProcessError):
            release.release("3.0.0", False)
        self.assertFalse(any(command[:2] == ("git", "push") for command in self.commands))
        self.assertFalse(any(command[:2] == ("gh", "release") for command in self.commands))

    def test_dirty_tree_never_mutates_versions(self):
        self.dirty = True
        with self.assertRaises(ValueError):
            release.release("3.0.0", False)
        self.assertEqual(self.project.read_text(), self.original)

    def test_changed_head_never_publishes(self):
        self.change_head = True
        with self.assertRaises(ValueError):
            release.release("3.0.0", False)
        self.assertFalse(any(command[:2] == ("git", "push") for command in self.commands))

    def test_bad_download_never_updates_tap(self):
        self.bad_download = True
        with self.assertRaises(ValueError):
            release.release("3.0.0", False)
        self.assertFalse(any(command[:2] == ("brew", "style") for command in self.commands))

    def test_resume_reuses_published_asset(self):
        self.existing = True
        self.project.write_text(release.bump_version(self.original, "3.0.0")[0])
        release.release("3.0.0", True)
        self.assertFalse(self.build_ran)
        self.assertFalse(any(command[:3] == ("gh", "release", "create") for command in self.commands))
        self.assertFalse(any(command[:3] == ("git", "tag", "-s") for command in self.commands))
        self.verify.assert_called_once()

    def test_resume_before_publication_does_not_bump_or_commit_again(self):
        updated = release.bump_version(self.original, "3.0.0")[0]
        self.project.write_text(updated)
        release.release("3.0.0", True)
        self.assertTrue(self.build_ran)
        self.assertEqual(self.project.read_text(), updated)
        commits = [command for command in self.commands if command[:2] == ("git", "commit")]
        self.assertEqual(len(commits), 1)  # Only the tap commit.
        self.assertIn("Update OpenInTerminal to 3.0.0", commits[0])

    def test_exported_bundle_versions_are_checked(self):
        app = self.root / "OpenInTerminal.app"
        paths = ["Contents/Info.plist", "Contents/PlugIns/Finder.appex/Contents/Info.plist",
                 "Contents/Library/LoginItems/Helper.app/Contents/Info.plist",
                 "Contents/Frameworks/Core.framework/Resources/Info.plist"]
        for name in paths:
            path = app / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(plistlib.dumps({"CFBundleShortVersionString": "3.0.0", "CFBundleVersion": "2"}))
        # Invoke the real validator while keeping codesign/stapler/spctl isolated.
        with patch.object(release, "run") as commands:
            VERIFY_APP(app, "3.0.0", "2")
            self.assertEqual(commands.call_count, 3)
            (app / paths[1]).write_bytes(plistlib.dumps({"CFBundleShortVersionString": "3.0.0", "CFBundleVersion": "1"}))
            commands.reset_mock()
            with self.assertRaises(ValueError):
                VERIFY_APP(app, "3.0.0", "2")
            commands.assert_not_called()


if __name__ == "__main__":
    unittest.main()
