"""Unit tests for the WhatsApp stats module."""

import unittest
from datetime import datetime
from src.stats import compute_stats, render_stats_html


class TestStats(unittest.TestCase):

    def setUp(self):
        self.messages = [
            {
                "date": "15/10/24 10:00:00",
                "sender": "Alice",
                "content": "Salut !",
                "dt": datetime(2024, 10, 15, 10, 0, 0),
            },
            {
                "date": "15/10/24 10:05:00",
                "sender": "Bob",
                "content": "Bonjour Alice, pièce jointe : IMG-PHOTO-1.jpg",
                "dt": datetime(2024, 10, 15, 10, 5, 0),
            },
            {
                "date": "15/10/24 11:00:00",
                "sender": "Alice",
                "content": "pièce jointe : AUD-AUDIO-1.opus",
                "dt": datetime(2024, 10, 15, 11, 0, 0),
            },
            {
                "date": "15/10/24 11:30:00",
                "sender": "Système",
                "content": "Les messages et les appels sont chiffrés de bout en bout.",
                "dt": datetime(2024, 10, 15, 11, 30, 0),
            },
        ]
        self.color_map = {"Alice": "#25D366", "Bob": "#128C7E"}

    def test_compute_stats(self):
        stats = compute_stats(self.messages)
        self.assertEqual(stats["total"], 4)
        # System message is excluded from real_total
        self.assertEqual(stats["real_total"], 3)
        self.assertEqual(stats["sender_counts"]["Alice"], 2)
        self.assertEqual(stats["sender_counts"]["Bob"], 1)
        self.assertEqual(stats["hour_counts"][10], 2)
        self.assertEqual(stats["hour_counts"][11], 1)
        self.assertIn("📷 Photo", stats["media_counts"])
        self.assertIn("🎤 Audio", stats["media_counts"])

    def test_render_stats_html(self):
        stats = compute_stats(self.messages)
        html_out = render_stats_html(stats, self.color_map)
        self.assertIn("<details class=\"stats-section\">", html_out)
        self.assertIn("Alice", html_out)
        self.assertIn("Bob", html_out)
        self.assertIn("Activité par heure", html_out)
        self.assertIn("Médias échangés", html_out)

    def test_compute_stats_empty(self):
        stats = compute_stats([])
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["real_total"], 0)
        self.assertEqual(len(stats["sender_counts"]), 0)
        self.assertEqual(stats["most_active"], ("", 0))

        # Ensure render_stats_html does not crash with ZeroDivisionError on empty stats
        html_out = render_stats_html(stats, {})
        self.assertIn("Statistiques de la conversation", html_out)
        self.assertIn("Aucun média", html_out)
        self.assertIn("N/A", html_out)

    def test_compute_stats_all_system_messages(self):
        messages = [
            {"date": "01/01/24 10:00:00", "sender": "Système", "content": "Les messages sont chiffrés de bout en bout.", "dt": None},
            {"date": "01/01/24 10:01:00", "sender": "Système", "content": "Appel vocal manqué", "dt": None},
        ]
        stats = compute_stats(messages)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["real_total"], 0)

        html_out = render_stats_html(stats, {})
        self.assertIn("0</strong>", html_out)

    def test_compute_stats_missing_dt(self):
        messages = [
            {"date": "date_invalide", "sender": "Alice", "content": "Hello", "dt": None},
            {"date": "date_invalide_2", "sender": "Alice", "content": "pièce jointe : clip.mp4", "dt": None},
        ]
        stats = compute_stats(messages)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["real_total"], 2)
        self.assertEqual(len(stats["hour_counts"]), 0)
        self.assertEqual(stats["media_counts"]["🎬 Vidéo"], 1)

    def test_render_stats_html_unknown_sender_color(self):
        messages = [{"date": "01/01/24 10:00:00", "sender": "Inconnu", "content": "Test", "dt": None}]
        stats = compute_stats(messages)
        # Empty color_map: should use fallback color #128C7E
        html_out = render_stats_html(stats, {})
        self.assertIn("#128C7E", html_out)
        self.assertIn("Inconnu", html_out)


if __name__ == "__main__":
    unittest.main()

