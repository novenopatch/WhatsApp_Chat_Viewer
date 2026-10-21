"""Unit tests for the WhatsApp config and user detector modules."""

import unittest
import tempfile
import os
from unittest.mock import patch
from src.config import parse_dotenv, find_chat_txt, parse_args, load_config, prompt_user
from src.user_detector import resolve_me_user, auto_detect_me



class TestConfig(unittest.TestCase):

    def test_parse_dotenv(self):
        content = """
        # Comment line
        CHAT_FILE=/path/to/chat.txt
        ME="John Doe"
        ANOTHER_KEY='value_single_quoted'
        PLAIN=simple_val
        """
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(content)
            temp_path = tf.name

        try:
            env = parse_dotenv(temp_path)
            self.assertEqual(env["CHAT_FILE"], "/path/to/chat.txt")
            self.assertEqual(env["ME"], "John Doe")
            self.assertEqual(env["ANOTHER_KEY"], "value_single_quoted")
            self.assertEqual(env["PLAIN"], "simple_val")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_find_chat_txt(self):
        with tempfile.TemporaryDirectory() as td:
            chat_path = os.path.join(td, "_chat.txt")
            with open(chat_path, "w", encoding="utf-8") as f:
                f.write("test")
            found = find_chat_txt(td)
            self.assertEqual(found, chat_path)

    def test_parse_args(self):
        # Long options
        args = parse_args([
            "--chat", "my_chat.txt",
            "--media", "my_media",
            "--output", "res.html",
            "--me", "Alice",
        ])
        self.assertEqual(args.chat, "my_chat.txt")
        self.assertEqual(args.media, "my_media")
        self.assertEqual(args.output, "res.html")
        self.assertEqual(args.me, "Alice")

        # Short options & aliases
        args_short = parse_args([
            "-c", "c.txt",
            "-d", "/path/to/dir",
            "-m", "m_dir",
            "-o", "out.html",
            "--your-name", "Bob",
        ])
        self.assertEqual(args_short.chat, "c.txt")
        self.assertEqual(args_short.dir, "/path/to/dir")
        self.assertEqual(args_short.media, "m_dir")
        self.assertEqual(args_short.output, "out.html")
        self.assertEqual(args_short.me, "Bob")

    def test_load_config_cli_priority(self):
        """CLI arguments must take priority over .env and default settings."""
        with tempfile.TemporaryDirectory() as td:
            chat_cli = os.path.join(td, "cli_chat.txt")
            with open(chat_cli, "w") as f:
                f.write("content")

            # Create a conflicting .env
            env_chat = os.path.join(td, "env_chat.txt")
            dotenv_file = os.path.join(td, ".env")
            with open(dotenv_file, "w") as f:
                f.write(f"CHAT_FILE={env_chat}\nME=FromEnv\n")

            orig_cwd = os.getcwd()
            try:
                os.chdir(td)
                chat, media, output, me, _ = load_config([
                    "--chat", chat_cli,
                    "--media", "cli_media",
                    "--output", "cli_out.html",
                    "--me", "FromCLI",
                ])
                self.assertEqual(chat, chat_cli)
                self.assertEqual(media, "cli_media")
                self.assertEqual(output, "cli_out.html")
                self.assertEqual(me, "FromCLI")
            finally:
                os.chdir(orig_cwd)

    def test_load_config_from_dotenv(self):
        """When no CLI args are given, settings should be loaded from .env."""
        with tempfile.TemporaryDirectory() as td:
            dotenv_file = os.path.join(td, ".env")
            with open(dotenv_file, "w") as f:
                f.write(
                    "CHAT_FILE=env_chat.txt\n"
                    "MEDIA_DIR=env_media\n"
                    "OUTPUT_FILE=env_out.html\n"
                    "ME=EnvAlice\n"
                )

            orig_cwd = os.getcwd()
            try:
                os.chdir(td)
                chat, media, output, me, _ = load_config([])
                self.assertEqual(chat, "env_chat.txt")
                self.assertEqual(media, "env_media")
                self.assertEqual(output, "env_out.html")
                self.assertEqual(me, "EnvAlice")
            finally:
                os.chdir(orig_cwd)

    def test_load_config_from_chat_dir(self):
        """Loading config with CHAT_DIR in .env or --dir on CLI discovers chat.txt and media/."""
        with tempfile.TemporaryDirectory() as td:
            sub_export = os.path.join(td, "export")
            os.makedirs(sub_export)
            chat_file = os.path.join(sub_export, "_chat.txt")
            with open(chat_file, "w") as f:
                f.write("test")
            media_folder = os.path.join(sub_export, "media")
            os.makedirs(media_folder)

            orig_cwd = os.getcwd()
            try:
                os.chdir(td)
                chat, media, output, me, _ = load_config(["--dir", sub_export])
                self.assertEqual(chat, chat_file)
                self.assertEqual(media, media_folder)
                self.assertTrue(output.endswith("output.html"))
            finally:
                os.chdir(orig_cwd)

    def test_find_chat_txt_edge_cases(self):
        # Non-existent dir
        self.assertIsNone(find_chat_txt("/non_existent_path_xyz_999"))

        with tempfile.TemporaryDirectory() as td:
            # Empty dir
            self.assertIsNone(find_chat_txt(td))

            # Non-chat txt
            other_txt = os.path.join(td, "notes.txt")
            with open(other_txt, "w") as f:
                f.write("notes")
            self.assertEqual(find_chat_txt(td), other_txt)

            # When _chat.txt is added, it must take precedence
            priority_txt = os.path.join(td, "_chat.txt")
            with open(priority_txt, "w") as f:
                f.write("priority")
            self.assertEqual(find_chat_txt(td), priority_txt)

    def test_prompt_user_non_interactive(self):
        with patch("sys.stdin.isatty", return_value=False):
            res = prompt_user("Enter name", default="DefaultUser")
            self.assertEqual(res, "DefaultUser")

    def test_prompt_user_interactive(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="CustomUser"):
            res = prompt_user("Enter name", default="DefaultUser")
            self.assertEqual(res, "CustomUser")

    def test_prompt_user_eof_error(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=EOFError):
            res = prompt_user("Enter name", default="DefaultUser")
            self.assertEqual(res, "DefaultUser")


    def test_resolve_me_user(self):
        attendees = ["Alice Dupont", "Bob Marley", "+33612345678", "~Charlie"]

        # Exact
        self.assertEqual(resolve_me_user("Alice Dupont", attendees), "Alice Dupont")
        # Case insensitive
        self.assertEqual(resolve_me_user("alice dupont", attendees), "Alice Dupont")
        # Substring
        self.assertEqual(resolve_me_user("Alice", attendees), "Alice Dupont")
        # Stripped prefix
        self.assertEqual(resolve_me_user("33612345678", attendees), "+33612345678")
        self.assertEqual(resolve_me_user("Charlie", attendees), "~Charlie")
        # None and empty
        self.assertIsNone(resolve_me_user(None, attendees))
        self.assertIsNone(resolve_me_user("", attendees))
        self.assertIsNone(resolve_me_user("   ", attendees))

    def test_auto_detect_me_all_strategies(self):
        # 1. Pronouns
        self.assertEqual(auto_detect_me(["Alice", "Bob", "Moi"]), "Moi")
        self.assertEqual(auto_detect_me(["Alice", "Bob", "Me"]), "Me")
        self.assertEqual(auto_detect_me(["Alice", "Bob", "Vous"]), "Vous")

        # 2. Context hint
        attendees2 = ["Alice", "Bob", "BlueTechTg"]
        self.assertEqual(auto_detect_me(attendees2, context_hint="/home/bluetechtg/chat"), "BlueTechTg")

        # 3. Empty list
        self.assertIsNone(auto_detect_me([]))


if __name__ == "__main__":
    unittest.main()

