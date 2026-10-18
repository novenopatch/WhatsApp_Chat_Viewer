"""CLI and End-to-End integration tests.

Tests the actual command-line interface execution via subprocess to ensure
that any refactoring never breaks command execution or return codes.
"""

import unittest
import subprocess
import sys
import os
import tempfile


class TestCLIAndIntegration(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.sample_chat = (
            "[01/01/2024 10:00:00] Alice: Test message 1\n"
            "[01/01/2024 10:01:00] Bob: Test message 2\n"
        )

    def test_cli_help(self):
        """Ensure `python3 build.py --help` runs without crashing and outputs usage."""
        cmd = [sys.executable, "build.py", "--help"]
        res = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("usage:", res.stdout.lower())
        self.assertIn("--chat", res.stdout)
        self.assertIn("--output", res.stdout)
        self.assertIn("--me", res.stdout)

    def test_cli_full_execution(self):
        """Ensure full CLI run produces an HTML file and exits with code 0."""
        with tempfile.TemporaryDirectory() as td:
            chat_file = os.path.join(td, "chat.txt")
            output_file = os.path.join(td, "output.html")
            with open(chat_file, "w", encoding="utf-8") as f:
                f.write(self.sample_chat)

            cmd = [
                sys.executable,
                "build.py",
                "--chat", chat_file,
                "--media", td,
                "--output", output_file,
                "--me", "Alice",
            ]
            res = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"CLI error: {res.stderr}")
            self.assertTrue(os.path.isfile(output_file))
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("Test message 1", content)
            self.assertIn("data-initial-me=\"Alice\"", content)

            # Ensure .gz compressed sibling file was generated and is valid
            gz_file = output_file + ".gz"
            self.assertTrue(os.path.isfile(gz_file))
            import gzip
            with gzip.open(gz_file, "rt", encoding="utf-8") as gz_f:
                gz_content = gz_f.read()
            self.assertEqual(gz_content, content)

    def test_cli_missing_chat_file_exits_with_error(self):
        """Ensure providing a non-existent chat file gracefully exits with status 1."""
        cmd = [
            sys.executable,
            "build.py",
            "--chat", "non_existent_file_xyz_123.txt",
            "--output", "dummy.html",
        ]
        res = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Fichier introuvable", res.stdout)

    def test_legacy_module_exports(self):
        """Ensure build.py still exposes backward-compatible functions and constants."""
        import build
        self.assertTrue(callable(build.parse_chat))
        self.assertTrue(callable(build.iter_chat))
        self.assertTrue(callable(build.build_html))
        self.assertTrue(callable(build.minify_html))
        self.assertTrue(callable(build.generate_thumbnails))
        self.assertTrue(callable(build.parse_date))
        self.assertTrue(callable(build.format_day_label))
        self.assertTrue(callable(build.compute_stats))
        self.assertTrue(callable(build.render_stats_html))
        self.assertTrue(callable(build.resolve_me_user))
        self.assertTrue(callable(build.auto_detect_me))
        self.assertTrue(callable(build.load_config))
        self.assertTrue(hasattr(build, "message_pattern"))
        self.assertTrue(hasattr(build, "AVATAR_COLORS"))


    def test_cli_with_dir_argument(self):
        """Ensure `python3 build.py --dir <folder>` automatically finds _chat.txt and media/."""
        with tempfile.TemporaryDirectory() as td:
            chat_file = os.path.join(td, "_chat.txt")
            with open(chat_file, "w", encoding="utf-8") as f:
                f.write(self.sample_chat)
            media_dir = os.path.join(td, "media")
            os.makedirs(media_dir)
            output_file = os.path.join(td, "out.html")

            cmd = [
                sys.executable,
                "build.py",
                "--dir", td,
                "--output", output_file,
            ]
            res = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertTrue(os.path.isfile(output_file))

    def test_cli_empty_chat_file_exits_error(self):
        """Ensure empty chat file gracefully exits with status 1."""
        with tempfile.TemporaryDirectory() as td:
            empty_chat = os.path.join(td, "empty.txt")
            with open(empty_chat, "w", encoding="utf-8") as f:
                f.write("\n\n\n")

            cmd = [
                sys.executable,
                "build.py",
                "--chat", empty_chat,
                "--output", os.path.join(td, "out.html"),
            ]
            res = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("Aucun message", res.stdout)


if __name__ == "__main__":
    unittest.main()

