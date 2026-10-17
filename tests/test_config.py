"""Unit tests for the WhatsApp config and user detector modules."""

import unittest
import tempfile
import os
from src.config import parse_dotenv, find_chat_txt
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

    def test_resolve_me_user(self):
        attendees = ["Alice Dupont", "Bob Marley", "+33612345678"]

        # Exact
        self.assertEqual(resolve_me_user("Alice Dupont", attendees), "Alice Dupont")
        # Case insensitive
        self.assertEqual(resolve_me_user("alice dupont", attendees), "Alice Dupont")
        # Substring
        self.assertEqual(resolve_me_user("Alice", attendees), "Alice Dupont")
        # Stripped prefix
        self.assertEqual(resolve_me_user("33612345678", attendees), "+33612345678")
        # None
        self.assertIsNone(resolve_me_user(None, attendees))
        self.assertIsNone(resolve_me_user("", attendees))

    def test_auto_detect_me(self):
        attendees = ["Alice", "Bob", "Moi"]
        self.assertEqual(auto_detect_me(attendees), "Moi")

        attendees2 = ["Alice", "Bob", "BlueTechTg"]
        self.assertEqual(auto_detect_me(attendees2, context_hint="/home/bluetechtg/chat"), "BlueTechTg")


if __name__ == "__main__":
    unittest.main()
