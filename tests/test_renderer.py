"""Unit tests for the WhatsApp renderer module."""

import unittest
from datetime import datetime
from src.renderer import (
    render_attachment,
    build_bubble,
    render_grouped_messages,
    build_html,
)


class TestRenderer(unittest.TestCase):

    def test_render_attachment_image(self):
        html_img = render_attachment("photo.jpg", "media", output_dir="")
        self.assertIn('<img src="media/photo.jpg"', html_img)
        self.assertIn('loading="lazy"', html_img)
        self.assertIn('class="media-img"', html_img)

    def test_render_attachment_audio(self):
        html_aud = render_attachment("voice.opus", "media", output_dir="")
        self.assertIn('<audio controls', html_aud)
        self.assertIn('audio-speed-btn', html_aud)

    def test_render_attachment_video(self):
        html_vid = render_attachment("clip.mp4", "media", output_dir="")
        self.assertIn('<video controls', html_vid)
        self.assertIn('media-video', html_vid)

    def test_render_attachment_sticker(self):
        html_stk = render_attachment("sticker.webp", "media", output_dir="")
        self.assertIn('sticker-img', html_stk)

    def test_build_bubble(self):
        bubble_other = build_bubble("Alice", "#25D366", "A", ["<div>Salut</div>"], is_me=False)
        self.assertIn('data-sender="Alice"', bubble_other)
        self.assertNotIn("is-me", bubble_other)

        bubble_me = build_bubble("Bob", "#128C7E", "B", ["<div>Hey</div>"], is_me=True)
        self.assertIn("message-row is-me", bubble_me)

    def test_render_grouped_messages(self):
        messages = [
            {
                "date": "15/10/24 10:00:00",
                "sender": "Alice",
                "content": "Message 1",
                "dt": datetime(2024, 10, 15, 10, 0, 0),
            },
            {
                "date": "15/10/24 10:01:00",
                "sender": "Alice",
                "content": "Message 2",
                "dt": datetime(2024, 10, 15, 10, 1, 0),
            },
            {
                "date": "15/10/24 10:05:00",
                "sender": "Bob",
                "content": "Réponse de Bob",
                "dt": datetime(2024, 10, 15, 10, 5, 0),
            },
        ]
        color_map = {"Alice": "#25D366", "Bob": "#128C7E"}
        html_out, attendees, (start_date, end_date) = render_grouped_messages(
            messages, "media", color_map, me_user="Bob"
        )
        self.assertEqual(len(attendees), 2)
        self.assertEqual(start_date, "15/10/24 10:00:00")
        self.assertEqual(end_date, "15/10/24 10:05:00")
        # Alice's 2 consecutive messages should be grouped in 1 row
        self.assertEqual(html_out.count('data-sender="Alice"'), 1)
        # Bob's message should have is-me
        self.assertIn("is-me", html_out)

    def test_build_html(self):
        messages = [
            {
                "date": "15/10/24 10:00:00",
                "sender": "Alice",
                "content": "Bonjour",
                "dt": datetime(2024, 10, 15, 10, 0, 0),
            }
        ]
        page = build_html(messages, "media", me_user="Alice")
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn("content-visibility: auto", page)
        self.assertIn("debounce", page)
        self.assertIn("Alice", page)


if __name__ == "__main__":
    unittest.main()
