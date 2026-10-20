"""Golden regression test for WhatsApp Chat Viewer.

Validates that any future code refactoring or enhancement does not break
expected structure, message counts, date separators, or media rendering.
"""

import unittest
import tempfile
import os
from src.parser import parse_chat
from src.stats import compute_stats
from src.renderer import build_html

SYNTHETIC_CHAT = """
[10/10/24 09:00:00] Alice: Salut Bob ! Tu as vu le *projet* ?
[10/10/24 09:01:00] Bob: Oui ! Voici la photo : pièce jointe : IMG-PHOTO-01.jpg
[10/10/24 09:02:00] Bob: Et voici la note vocale : pièce jointe : AUD-AUDIO-02.opus
[10/10/24 09:03:00] Charlie: Bonjour tout le monde, vidéo ici : pièce jointe : VID-VIDEO-03.mp4
[10/10/24 09:04:00] Charlie: pièce jointe : STK-STICKER-04.webp
[10/10/24 09:05:00] Système: Les messages et les appels sont chiffrés de bout en bout.
[10/10/24 09:06:00] Alice: Appel vocal manqué
[11/10/24 10:00:00] Bob: Nouveau jour !
Regarde ce lien : https://example.com/docs
[11/10/24 10:01:00] Bob: Message rectifié <Ce message a été modifié>
[11/10/24 10:02:00] Alice: Code d'exemple :
```
def hello():
    print("world")
```
"""


class TestRegressionGolden(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(SYNTHETIC_CHAT.strip())
            self.chat_path = tf.name

    def tearDown(self):
        if os.path.exists(self.chat_path):
            os.remove(self.chat_path)

    def test_complete_golden_pipeline(self):
        # 1. Parse
        messages = parse_chat(self.chat_path)
        self.assertEqual(len(messages), 10, "Expected exactly 10 parsed messages!")

        # 2. Stats
        stats = compute_stats(messages)
        self.assertEqual(stats["total"], 10)
        # 2 system messages (chiffrés, appel manqué)
        self.assertEqual(stats["real_total"], 8)
        self.assertEqual(len(stats["sender_counts"]), 3)  # Alice, Bob, Charlie

        # 3. HTML Rendering (Default English)
        html = build_html(messages, "media", me_user="Alice")

        # HTML Structure invariants
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertTrue(html.rstrip().endswith("</html>"))

        # Date separators: 2 distinct days (10/10/24 and 11/10/24) in English
        self.assertEqual(html.count('class="date-separator"'), 2)
        self.assertIn("Thursday 10 October 2024", html)
        self.assertIn("Friday 11 October 2024", html)

        # System messages: 2 system messages styled with icon pill
        self.assertEqual(html.count('class="system-message"'), 2)
        self.assertIn("🔒", html)
        self.assertIn("📞", html)

        # Media renderings
        self.assertIn('<img src="media/IMG-PHOTO-01.jpg" class="media-img"', html)
        self.assertIn('<audio controls', html)
        self.assertIn('<button type="button" class="audio-speed-btn"', html)
        self.assertIn('<video controls', html)
        self.assertIn('<img src="media/STK-STICKER-04.webp" class="sticker-img"', html)

        # Markdown & formatting
        self.assertIn("<strong>projet</strong>", html)
        self.assertIn('<a href="https://example.com/docs"', html)
        self.assertIn('<pre><code>', html)
        self.assertIn('<span class="edited-badge">edited</span>', html)

        # User identification & classes
        self.assertIn('data-initial-me="Alice"', html)
        self.assertIn('message-row is-me" data-sender="Alice"', html)

        # 4. Multilingual HTML Rendering (French)
        html_fr = build_html(messages, "media", me_user="Alice", lang="fr")
        self.assertIn("Jeudi 10 octobre 2024", html_fr)
        self.assertIn("Vendredi 11 octobre 2024", html_fr)
        self.assertIn('<span class="edited-badge">modifié</span>', html_fr)


    def test_realistic_whatsapp_export_pipeline(self):
        """Test with realistic export patterns: LTR invisible chars, brackets in attachments, phone numbers."""
        chat_content = (
            "[9/17/24 21:36:14] +33612345678: \u200eLes messages et les appels sont chiffrés de bout en bout.\n"
            "[9/17/24 21:36:14] +33612345678: \u200eAppel vidéo, \u200e5 min\n"
            "\u200e[9/21/24 08:17:10] BlueTechTg: \u200e< pièce jointe : 00000012-AUDIO-2024-09-21-08-17-09.opus >\n"
            "\u200e[9/21/24 13:00:52] +33612345678: \u200e< pièce jointe : 00000016-PHOTO-2024-09-21-13-00-52.jpg >\n"
            "[9/21/24 13:03:13] +33612345678: \u200eAppel vocal manqué, \u200eAppuyez pour rappeler\n"
            "[9/21/24 13:15:14] +33612345678: merci mon coeur\n"
        )
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(chat_content)
            temp_path = tf.name

        try:
            msgs = parse_chat(temp_path)
            self.assertEqual(len(msgs), 6)
            stats = compute_stats(msgs)
            self.assertEqual(stats["total"], 6)
            # 3 system messages: chiffrés, appel vidéo, appel vocal manqué
            self.assertEqual(stats["real_total"], 3)
            self.assertEqual(stats["media_counts"]["🎤 Audio"], 1)
            self.assertEqual(stats["media_counts"]["📷 Photo"], 1)

            html_page = build_html(msgs, "media", me_user="BlueTechTg")
            self.assertIn("00000012-AUDIO-2024-09-21-08-17-09.opus", html_page)
            self.assertIn("00000016-PHOTO-2024-09-21-13-00-52.jpg", html_page)
            self.assertIn("data-sender=\"BlueTechTg\"", html_page)
            self.assertIn("data-sender=\"+33612345678\"", html_page)
            self.assertIn("is-me", html_page)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()

