"""Unit tests for the WhatsApp parser module."""

import unittest
import tempfile
import os
from datetime import datetime
from src.parser import (
    parse_date,
    format_day_label,
    get_attachment_filename,
    is_system_message,
    get_system_icon,
    get_media_type_label,
    format_message,
    strip_annotations,
    parse_chat,
)


class TestParser(unittest.TestCase):

    def test_parse_date_valid(self):
        dt1 = parse_date("15/10/24 14:30:15")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1, datetime(2024, 10, 15, 14, 30, 15))

        dt2 = parse_date("15/10/2024 09:05:00")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2, datetime(2024, 10, 15, 9, 5, 0))

        # Unicode whitespace / marks handling
        dt3 = parse_date("\u200e15/10/24 14:30:15 ")
        self.assertIsNotNone(dt3)

    def test_parse_date_invalid(self):
        self.assertIsNone(parse_date("not-a-date"))
        self.assertIsNone(parse_date("99/99/99 99:99:99"))

    def test_format_day_label(self):
        dt = datetime(2024, 3, 4)  # 2024-03-04 is Monday
        label = format_day_label(dt)
        self.assertEqual(label, "Lundi 4 mars 2024")

    def test_get_attachment_filename(self):
        self.assertEqual(
            get_attachment_filename("pièce jointe : photo.jpg"),
            "photo.jpg"
        )
        self.assertEqual(
            get_attachment_filename("\u200epiece jointe : audio.opus (file attached: audio.opus)"),
            "audio.opus"
        )
        self.assertIsNone(get_attachment_filename("Just a regular message"))

    def test_is_system_message(self):
        self.assertTrue(is_system_message("Les messages sont chiffrés de bout en bout."))
        self.assertTrue(is_system_message("Appel vocal manqué"))
        self.assertTrue(is_system_message("Ce message a été supprimé"))
        self.assertFalse(is_system_message("Salut comment ça va ?"))

    def test_get_system_icon(self):
        self.assertEqual(get_system_icon("Appel vocal manqué"), "📞")
        self.assertEqual(get_system_icon("Appel vidéo"), "📹")
        self.assertEqual(get_system_icon("Messages chiffrés"), "🔒")
        self.assertEqual(get_system_icon("Autre événement inconnu"), "ℹ️")

    def test_get_media_type_label(self):
        self.assertEqual(get_media_type_label("IMG-PHOTO-123.jpg"), "📷 Photo")
        self.assertEqual(get_media_type_label("AUD-AUDIO-123.opus"), "🎤 Audio")
        self.assertEqual(get_media_type_label("VID-VIDEO-123.mp4"), "🎬 Vidéo")
        self.assertEqual(get_media_type_label("STK-STICKER-123.webp"), "🎭 Sticker")
        self.assertEqual(get_media_type_label("document.pdf"), "📎 Autre")

    def test_format_message_markdown(self):
        html_bold = format_message("*texte gras*")
        self.assertIn("<strong>texte gras</strong>", html_bold)

        html_italic = format_message("_italique_")
        self.assertIn("<em>italique</em>", html_italic)

        html_strike = format_message("~barré~")
        self.assertIn("<del>barré</del>", html_strike)

        html_code = format_message("`mono`")
        self.assertIn("<code>mono</code>", html_code)

        html_block = format_message("```bloc de code```")
        self.assertIn("<pre><code>bloc de code</code></pre>", html_block)

    def test_format_message_html_escaping(self):
        unsafe = "<script>alert('xss')</script>"
        res = format_message(unsafe)
        self.assertNotIn("<script>", res)
        self.assertIn("&lt;script&gt;", res)

    def test_format_message_links(self):
        msg = "Consulte https://google.com pour chercher."
        res = format_message(msg)
        self.assertIn('<a href="https://google.com" target="_blank"', res)

    def test_strip_annotations(self):
        msg = "Texte modifié <Ce message a été modifié>"
        cleaned, was_edited = strip_annotations(msg)
        self.assertTrue(was_edited)
        self.assertEqual(cleaned, "Texte modifié")

        msg_normal = "Message ordinaire"
        cleaned2, was_edited2 = strip_annotations(msg_normal)
        self.assertFalse(was_edited2)
        self.assertEqual(cleaned2, "Message ordinaire")

    def test_parse_chat_simple(self):
        sample = (
            "[15/10/24 14:00:00] Alice: Bonjour !\n"
            "[15/10/24 14:01:00] Bob: Salut Alice,\n"
            "Comment vas-tu ?\n"
        )
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(sample)
            temp_path = tf.name

        try:
            messages = parse_chat(temp_path)
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["sender"], "Alice")
            self.assertEqual(messages[0]["content"], "Bonjour !")
            self.assertEqual(messages[1]["sender"], "Bob")
            self.assertIn("Comment vas-tu ?", messages[1]["content"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
