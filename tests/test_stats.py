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


if __name__ == "__main__":
    unittest.main()
