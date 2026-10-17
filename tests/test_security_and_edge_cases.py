"""Security, XSS, injection, and weird edge-case tests.

Ensures that refactoring or new features cannot introduce XSS vulnerabilities,
crashes on unexpected inputs, or data corruption.
"""

import unittest
from datetime import datetime
from src.parser import (
    format_message,
    strip_annotations,
    get_attachment_filename,
    parse_date,
    is_system_message,
)
from src.renderer import (
    build_bubble,
    render_attachment,
    build_html,
    render_grouped_messages,
)
from src.constants import AVATAR_COLORS


class TestSecurityAndEdgeCases(unittest.TestCase):

    def test_xss_in_message_content(self):
        """Ensure malicious HTML/JS payloads inside message content are strictly escaped."""
        xss_payloads = [
            "<script>alert(1)</script>",
            '<img src=x onerror="alert(\'xss\')">',
            "<iframe src=\"javascript:alert(1)\"></iframe>",
            "<a href=\"javascript:alert('xss')\">click</a>",
            "<b>hello</b><style>body{display:none;}</style>",
            "*\"><script>alert(1)</script>*",
        ]
        for payload in xss_payloads:
            result = format_message(payload)
            self.assertNotIn("<script>", result.lower())
            self.assertNotIn("<iframe", result.lower())
            self.assertNotIn("<style>", result.lower())
            self.assertNotIn("<img", result.lower())

    def test_xss_in_sender_name(self):
        """Ensure malicious characters in sender names are properly escaped in bubbles and headers."""
        evil_sender = '<script>alert("evil")</script> & "Admin"'
        bubble = build_bubble(evil_sender, "#123456", "EA", ["<div>msg</div>"], is_me=False)
        self.assertNotIn("<script>", bubble)
        self.assertIn("&lt;script&gt;", bubble)
        self.assertIn("&quot;Admin&quot;", bubble)

    def test_xss_in_filename(self):
        """Ensure malicious filenames do not lead to arbitrary HTML injection."""
        evil_filename = 'photo"><script>alert(1)</script>.jpg'
        html_snippet = render_attachment(evil_filename, "media")
        self.assertNotIn("<script>", html_snippet)
        self.assertIn("&quot;&gt;&lt;script&gt;", html_snippet)

    def test_avatar_colors_modulo_overflow(self):
        """Test with 50 unique participants to ensure AVATAR_COLORS modulo never raises IndexError."""
        attendees = [f"User_{i}" for i in range(50)]
        color_map = {
            name: AVATAR_COLORS[idx % len(AVATAR_COLORS)]
            for idx, name in enumerate(attendees)
        }
        self.assertEqual(len(color_map), 50)
        for name in attendees:
            self.assertIn(color_map[name], AVATAR_COLORS)

    def test_unicode_invisible_marks(self):
        """WhatsApp often includes LTR and RTL invisible marks (\u200e, \u202a, \u202c, \u202f)."""
        date_str = "\u200e\u202f15/10/24 14:00:00\u200e"
        dt = parse_date(date_str)
        self.assertIsNotNone(dt)

        raw_att = "\u200e\u202apièce jointe : \u202ctest.jpg\u202c"
        att = get_attachment_filename(raw_att)
        self.assertEqual(att, "test.jpg")

    def test_empty_and_whitespace_messages(self):
        """Ensure empty strings and weird whitespaces don't crash the renderer."""
        cleaned, edited = strip_annotations("   \n\t  ")
        self.assertEqual(cleaned, "")
        self.assertFalse(edited)

        # Empty messages list to build_html
        html_out = build_html([], "media")
        self.assertIn("Aucun message", html_out)

    def test_multiline_code_blocks_and_markdown_nesting(self):
        """Ensure code blocks and mixed formatting don't produce corrupted tags."""
        raw = "```\ndef foo():\n    return 'bar'\n```\nEt du *gras avec du _italique_*."
        out = format_message(raw)
        self.assertIn("<pre><code>", out)
        self.assertIn("def foo():", out)
        self.assertIn("<strong>", out)

    def test_special_characters_in_me_user(self):
        """Ensure me_user with quotes or apostrophes doesn't break JavaScript or HTML attributes."""
        messages = [
            {
                "date": "15/10/24 10:00:00",
                "sender": "L'Ami d'Alice \"VIP\"",
                "content": "Coucou",
                "dt": datetime(2024, 10, 15, 10, 0, 0),
            }
        ]
        html_out = build_html(messages, "media", me_user="L'Ami d'Alice \"VIP\"")
        self.assertIn("L&#x27;Ami d&#x27;Alice &quot;VIP&quot;", html_out)
        self.assertIn("data-initial-me=\"L&#x27;Ami d&#x27;Alice &quot;VIP&quot;\"", html_out)


    def test_unclosed_markdown_markers(self):
        """Unclosed formatting characters should remain literal text without crashing or broken tags."""
        unclosed = "*gras sans fin et _italique sans fin et ~barre et `mono"
        out = format_message(unclosed)
        self.assertNotIn("<strong>", out)
        self.assertNotIn("<em>", out)
        self.assertNotIn("<del>", out)
        self.assertNotIn("<code>", out)
        self.assertIn("*gras sans fin", out)

    def test_url_with_query_parameters_and_symbols(self):
        """URLs with query parameters (&, =, ?, #) should be safely escaped in href and displayed."""
        raw_url = "Consultez https://example.com/test?a=1&b=2#section"
        out = format_message(raw_url)
        self.assertIn('href="https://example.com/test?a=1&amp;b=2#section"', out)


if __name__ == "__main__":
    unittest.main()

