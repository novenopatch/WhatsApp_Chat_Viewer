"""Unit tests for WhatsApp Quotes (Citations) and Reactions (Emojis)."""

import os
import tempfile
import unittest
from datetime import datetime
from src.parser import (
    format_message,
    format_inline_markdown,
    parse_reaction_notification,
    extract_trailing_reactions,
    resolve_quote_target_id,
    process_chat_reactions,
    parse_chat,
)
from src.renderer import (
    render_reactions_html,
    render_grouped_messages,
    build_html,
)


class TestQuotesAndReactions(unittest.TestCase):

    def test_quote_with_author(self):
        raw = "> Alice: On se voit demain ?\nOui super !"
        out = format_message(raw)
        self.assertIn('class="wa-quote-box"', out)
        self.assertIn('data-quoted-author="Alice"', out)
        self.assertIn('<div class="wa-quote-author">Alice</div>', out)
        self.assertIn('On se voit demain ?', out)
        self.assertIn('Oui super !', out)

    def test_quote_anonymous(self):
        raw = "> Ceci est une citation sans auteur\nRéponse ici."
        out = format_message(raw)
        self.assertIn('class="wa-quote-box"', out)
        self.assertNotIn('data-quoted-author', out)
        self.assertIn('Ceci est une citation sans auteur', out)
        self.assertIn('Réponse ici.', out)

    def test_quote_multiline(self):
        raw = "> Ligne 1 de la citation\n> Ligne 2 de la citation\nTexte après citation."
        out = format_message(raw)
        self.assertIn('class="wa-quote-box"', out)
        self.assertIn('Ligne 1 de la citation<br>Ligne 2 de la citation', out)
        self.assertIn('Texte après citation.', out)

    def test_quote_with_markdown_inside(self):
        raw = "> Alice: Regarde *ceci* et https://example.com\nReçu !"
        out = format_message(raw)
        self.assertIn('<strong>ceci</strong>', out)
        self.assertIn('<a href="https://example.com"', out)
        self.assertIn('Reçu !', out)

    def test_quote_target_id_resolution(self):
        messages = [
            {"sender": "Alice", "content": "Rendez-vous à 15h.", "date": "10/10/24 10:00:00"},
            {"sender": "Bob", "content": "> Alice: Rendez-vous à 15h.\nParfait !", "date": "10/10/24 10:01:00"},
        ]
        target_id = resolve_quote_target_id(messages, 1, messages[1]["content"])
        self.assertEqual(target_id, "msg-0")

        # Formatted output embeds data-target-id
        out = format_message(messages[1]["content"], quote_target_id=target_id)
        self.assertIn('data-target-id="msg-0"', out)

    def test_reaction_notification_english(self):
        res1 = parse_reaction_notification('❤️ to "Hello world"')
        self.assertIsNotNone(res1)
        self.assertEqual(res1, ("❤️", "Hello world"))

        res2 = parse_reaction_notification('reacted with 😂 to "That is funny"')
        self.assertIsNotNone(res2)
        self.assertEqual(res2, ("😂", "That is funny"))

        res3 = parse_reaction_notification('👍 to “Smart move”')
        self.assertIsNotNone(res3)
        self.assertEqual(res3, ("👍", "Smart move"))

    def test_reaction_notification_french(self):
        res1 = parse_reaction_notification('a réagi par 👍 à "D\'accord"')
        self.assertIsNotNone(res1)
        self.assertEqual(res1, ("👍", "D'accord"))

        res2 = parse_reaction_notification('a réagi avec ❤️ à "Merci beaucoup"')
        self.assertIsNotNone(res2)
        self.assertEqual(res2, ("❤️", "Merci beaucoup"))

        res3 = parse_reaction_notification('a réagi 😂 à "Hahaha"')
        self.assertIsNotNone(res3)
        self.assertEqual(res3, ("😂", "Hahaha"))

    def test_trailing_reactions_brackets(self):
        content = "Génial l'idée ! [❤️]"
        cleaned, reactions = extract_trailing_reactions(content, sender="Bob")
        self.assertEqual(cleaned, "Génial l'idée !")
        self.assertEqual(len(reactions), 1)
        self.assertEqual(reactions[0]["emoji"], "❤️")
        self.assertEqual(reactions[0]["sender"], "Bob")

    def test_trailing_reactions_parentheses(self):
        content = "Tout à fait d'accord (👍, 🔥)"
        cleaned, reactions = extract_trailing_reactions(content, sender="Alice")
        self.assertEqual(cleaned, "Tout à fait d'accord")
        self.assertEqual(len(reactions), 2)
        self.assertEqual(reactions[0]["emoji"], "👍")
        self.assertEqual(reactions[1]["emoji"], "🔥")

    def test_trailing_reactions_with_named_senders(self):
        content = "Voici la photo [Reactions: Alice 👍, Bob ❤️]"
        cleaned, reactions = extract_trailing_reactions(content, sender="System")
        self.assertEqual(cleaned, "Voici la photo")
        self.assertEqual(len(reactions), 2)
        self.assertEqual(reactions[0]["emoji"], "👍")
        self.assertEqual(reactions[0]["sender"], "Alice")
        self.assertEqual(reactions[1]["emoji"], "❤️")
        self.assertEqual(reactions[1]["sender"], "Bob")

    def test_process_chat_reactions_linking(self):
        msgs = [
            {"sender": "Alice", "content": "Bienvenue dans l'équipe !"},
            {"sender": "Bob", "content": "Merci [🙏]"},
            {"sender": "Charlie", "content": "❤️ to \"Bienvenue dans l'équipe !\""},
            {"sender": "David", "content": "a réagi par 🎉 à \"Bienvenue dans l'équipe !\""},
        ]
        processed = process_chat_reactions(msgs)

        # Alice's message should have Charlie's ❤️ and David's 🎉
        alice_reactions = processed[0].get("reactions", [])
        self.assertEqual(len(alice_reactions), 2)
        self.assertEqual(alice_reactions[0]["emoji"], "❤️")
        self.assertEqual(alice_reactions[0]["sender"], "Charlie")
        self.assertEqual(alice_reactions[1]["emoji"], "🎉")
        self.assertEqual(alice_reactions[1]["sender"], "David")

        # Bob's trailing reaction should be extracted
        bob_reactions = processed[1].get("reactions", [])
        self.assertEqual(len(bob_reactions), 1)
        self.assertEqual(bob_reactions[0]["emoji"], "🙏")
        self.assertEqual(processed[1]["content"], "Merci")

        # Reaction event messages should be flagged as events
        self.assertTrue(processed[2].get("is_reaction_event"))
        self.assertEqual(processed[2].get("reaction_target_id"), "msg-0")
        self.assertTrue(processed[3].get("is_reaction_event"))
        self.assertEqual(processed[3].get("reaction_target_id"), "msg-0")

    def test_render_reactions_html(self):
        reactions = [
            {"emoji": "❤️", "sender": "Alice"},
            {"emoji": "❤️", "sender": "Bob"},
            {"emoji": "👍", "sender": "Charlie"},
        ]
        html_out = render_reactions_html(reactions, "msg-5")
        self.assertIn('data-msg-id="msg-5"', html_out)
        self.assertIn('class="wa-reaction-pill"', html_out)
        self.assertIn('data-emoji="❤️"', html_out)
        self.assertIn('Alice, Bob: ❤️', html_out)
        self.assertIn('>2</span>', html_out)  # 2 count for heart
        self.assertIn('data-emoji="👍"', html_out)
        self.assertIn('Charlie: 👍', html_out)
        self.assertIn('>1</span>', html_out)  # 1 count for thumbs up

    def test_render_grouped_messages_with_quotes_and_reactions(self):
        messages = [
            {
                "date": "15/10/24 10:00:00",
                "sender": "Alice",
                "content": "On commence la réunion ?",
                "dt": datetime(2024, 10, 15, 10, 0, 0),
            },
            {
                "date": "15/10/24 10:01:00",
                "sender": "Bob",
                "content": "> Alice: On commence la réunion ?\nOui, c'est parti !",
                "dt": datetime(2024, 10, 15, 10, 1, 0),
            },
            {
                "date": "15/10/24 10:02:00",
                "sender": "Charlie",
                "content": "❤️ to \"On commence la réunion ?\"",
                "dt": datetime(2024, 10, 15, 10, 2, 0),
            },
        ]
        html_res, attendees, _ = render_grouped_messages(messages, "media", {"Alice": "#111", "Bob": "#222", "Charlie": "#333"})

        # Quote box rendered with target id link
        self.assertIn('class="wa-quote-box"', html_res)
        self.assertIn('data-target-id="msg-0"', html_res)
        self.assertIn('Alice', html_res)
        self.assertIn("Oui, c&#x27;est parti !", html_res)

        # Charlie's reaction absorbed onto Alice's message (msg-0)
        self.assertIn('data-emoji="❤️"', html_res)
        self.assertIn('Charlie: ❤️', html_res)

        # Reaction trigger button present
        self.assertIn('class="wa-react-btn"', html_res)

    def test_xss_safety_in_quotes_and_reactions(self):
        evil_quote = '> <script>alert("quote")</script>: evil content <img src=x onerror=alert(1)>\nRéponse'
        out = format_message(evil_quote)
        self.assertNotIn("<script>", out.lower())
        self.assertNotIn("<img", out.lower())
        self.assertIn("&lt;script&gt;", out)

        evil_reactions = [
            {"emoji": "❤️", "sender": '<script>alert("evil")</script>'}
        ]
        r_html = render_reactions_html(evil_reactions, "msg-0")
        self.assertNotIn("<script>", r_html)
        self.assertIn("&lt;script&gt;", r_html)

    def test_golden_integration_pipeline_with_quotes_and_reactions(self):
        sample = (
            "[15/10/24 10:00:00] Alice: Salut tout le monde !\n"
            "[15/10/24 10:00:30] Bob: Salut Alice [👍]\n"
            "[15/10/24 10:01:00] Charlie: ❤️ to \"Salut tout le monde !\"\n"
            "[15/10/24 10:02:00] Alice: > Bob: Salut Alice\nComment vas-tu ?\n"
        )
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(sample)
            chat_file = tf.name

        try:
            messages = parse_chat(chat_file)
            self.assertEqual(len(messages), 4)
            full_html = build_html(messages, "media")

            # Contains reaction picker
            self.assertIn('id="reaction-picker"', full_html)
            self.assertIn('wa-picker-emoji', full_html)

            # Contains quote box
            self.assertIn('wa-quote-box', full_html)

            # Contains reaction badges
            self.assertIn('wa-reaction-pill', full_html)
        finally:
            if os.path.exists(chat_file):
                os.remove(chat_file)


if __name__ == "__main__":
    unittest.main()
