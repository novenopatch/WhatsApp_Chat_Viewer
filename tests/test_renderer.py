"""Unit tests for the WhatsApp renderer module."""

import os
import tempfile
import unittest
from datetime import datetime
from src.renderer import (
    render_attachment,
    build_bubble,
    render_grouped_messages,
    build_html,
    minify_html,
    generate_thumbnails,
    HAS_PIL,
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


    def test_render_attachment_relative_output_dir(self):
        html_out = render_attachment("photo.jpg", "/tmp/export/media", output_dir="/tmp/export/html")
        self.assertIn('src="../media/photo.jpg"', html_out)

    def test_render_attachment_pdf_and_other(self):
        pdf_out = render_attachment("doc.pdf", "media")
        self.assertIn('📄 doc.pdf', pdf_out)
        self.assertIn('target="_blank"', pdf_out)

        zip_out = render_attachment("archive.zip", "media")
        self.assertIn('📎 archive.zip', zip_out)

    def test_render_grouped_messages_date_change(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Jour 1", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "16/10/24 10:00:00", "sender": "Alice", "content": "Jour 2", "dt": datetime(2024, 10, 16, 10, 0, 0)},
        ]
        html_out, _, _ = render_grouped_messages(messages, "media", {"Alice": "#123"})
        self.assertEqual(html_out.count('class="date-separator"'), 2)
        # Should be two separate bubbles because the day changed
        self.assertEqual(html_out.count('data-sender="Alice"'), 2)

    def test_render_grouped_messages_system_message_interruption(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Avant système", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "15/10/24 10:01:00", "sender": "Système", "content": "Appel vocal manqué", "dt": datetime(2024, 10, 15, 10, 1, 0)},
            {"date": "15/10/24 10:02:00", "sender": "Alice", "content": "Après système", "dt": datetime(2024, 10, 15, 10, 2, 0)},
        ]
        html_out, _, _ = render_grouped_messages(messages, "media", {"Alice": "#123", "Système": "#999"})
        self.assertIn('class="system-message"', html_out)
        # Should be 2 distinct bubbles for Alice separated by the system pill
        self.assertEqual(html_out.count('data-sender="Alice"'), 2)

    def test_build_html_empty_messages(self):
        page_en = build_html([], "media")
        self.assertIn("No messages", page_en)
        page_fr = build_html([], "media", lang="fr")
        self.assertIn("Aucun message", page_fr)

    def test_build_html_group_vs_duo(self):
        # 2 participants -> English default & French
        duo = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Hi", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "15/10/24 10:01:00", "sender": "Bob", "content": "Hello", "dt": datetime(2024, 10, 15, 10, 1, 0)},
        ]
        html_duo_en = build_html(duo, "media")
        self.assertIn("WhatsApp Conversation - Alice &amp; Bob", html_duo_en)

        html_duo_fr = build_html(duo, "media", lang="fr")
        self.assertIn("Conversation WhatsApp - Alice &amp; Bob", html_duo_fr)

        # 3 participants -> WhatsApp Group Conversation
        group = duo + [{"date": "15/10/24 10:02:00", "sender": "Charlie", "content": "Yo", "dt": datetime(2024, 10, 15, 10, 2, 0)}]
        html_group_en = build_html(group, "media")
        self.assertIn("WhatsApp Group Conversation - Alice &amp; Bob &amp; Charlie", html_group_en)

        html_group_fr = build_html(group, "media", lang="fr")
        self.assertIn("Conversation de groupe WhatsApp - Alice &amp; Bob &amp; Charlie", html_group_fr)

    def test_build_html_all_placeholders_replaced(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Test", "dt": datetime(2024, 10, 15, 10, 0, 0)}
        ]
        page = build_html(messages, "media", me_user="Alice")
        self.assertNotIn("{{", page)
        self.assertNotIn("}}", page)

    def test_build_html_me_selector_and_legend(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Hi", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "15/10/24 10:01:00", "sender": "Bob", "content": "Hey", "dt": datetime(2024, 10, 15, 10, 1, 0)},
        ]
        page = build_html(messages, "media", me_user="Alice")
        self.assertIn('<option value="Alice" selected="selected">Alice</option>', page)
        self.assertIn('<option value="Bob">Bob</option>', page)
        self.assertIn('setMeUser(\'Alice\')', page)
        self.assertIn('setMeUser(\'Bob\')', page)


    def test_gallery_data_collection_and_rendering(self):
        import json
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Regarde la photo : pièce jointe : img1.jpg", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "15/10/24 10:01:00", "sender": "Bob", "content": "Voici la vidéo : pièce jointe : vid1.mp4", "dt": datetime(2024, 10, 15, 10, 1, 0)},
            {"date": "15/10/24 10:02:00", "sender": "Bob", "content": "Note vocale : pièce jointe : voice.opus", "dt": datetime(2024, 10, 15, 10, 2, 0)},
            {"date": "15/10/24 10:03:00", "sender": "Alice", "content": "Doc PDF : pièce jointe : report.pdf", "dt": datetime(2024, 10, 15, 10, 3, 0)},
            {"date": "15/10/24 10:04:00", "sender": "Alice", "content": "Lien utile : https://google.com/test", "dt": datetime(2024, 10, 15, 10, 4, 0)},
        ]
        html_page = build_html(messages, "media", me_user="Alice")
        self.assertIn('id="gallery-modal"', html_page)
        self.assertIn('id="gallery-data"', html_page)
        self.assertIn('id="gallery-count-badge"', html_page)

        # Check gallery-data JSON content
        data_script = html_page.split('id="gallery-data" type="application/json">')[1].split('</script>')[0]
        data = json.loads(data_script)
        self.assertEqual(len(data["photos"]), 2)  # img1.jpg and vid1.mp4
        self.assertTrue(data["photos"][1]["video"])
        self.assertEqual(len(data["audios"]), 1)  # voice.opus
        self.assertEqual(len(data["docs"]), 1)    # report.pdf
        self.assertEqual(len(data["links"]), 1)   # google.com

        # Check msgId present for jump-to-message
        for category in ("photos", "audios", "docs", "links"):
            for item in data[category]:
                self.assertTrue(item.get("msgId", "").startswith("msg-"))

    def test_advanced_filters_dom_and_attributes(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Salut", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "15/10/24 10:05:00", "sender": "Bob", "content": "Photo : pièce jointe : test.png", "dt": datetime(2024, 10, 15, 10, 5, 0)},
        ]
        html_page = build_html(messages, "media", me_user="Alice")
        # Check filter bar elements
        self.assertIn('id="filter-bar"', html_page)
        self.assertIn('id="filter-sender"', html_page)
        self.assertIn('id="filter-month"', html_page)
        self.assertIn('id="filter-media-only"', html_page)
        self.assertIn('id="filter-reset"', html_page)

        # Check date separator and message row data attributes
        self.assertIn('class="date-separator" data-date="2024-10-15" data-month="2024-10"', html_page)
        self.assertIn('data-has-media="true"', html_page)
        self.assertIn('data-has-media="false"', html_page)

    def test_whatsapp_doodle_wallpaper_and_lightbox_features(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Clip : pièce jointe : movie.mp4", "dt": datetime(2024, 10, 15, 10, 0, 0)}
        ]
        html_page = build_html(messages, "media", me_user="Alice")
        # Wallpaper button and CSS
        self.assertIn('id="wallpaper-toggle"', html_page)
        self.assertIn('body.wallpaper-on', html_page)
        self.assertIn('body.dark-mode.wallpaper-on', html_page)

        # Lightbox elements: image, video, fullscreen button
        self.assertIn('id="lightbox"', html_page)
        self.assertIn('id="lightbox-img"', html_page)
        self.assertIn('id="lightbox-video"', html_page)
        self.assertIn('id="lb-fullscreen"', html_page)
        self.assertIn('id="lb-actual-size"', html_page)
        self.assertIn('id="lb-open-hd"', html_page)
        self.assertIn('class="video-fs-btn"', html_page)

    def test_minify_html(self):
        sample = """<!DOCTYPE html>
<html>
    <head>
        <!-- Test Comment -->
        <style>
            .test { color: red; }
        </style>
    </head>
    <body>
        <div class="msg">
            <pre><code>code block preserves   spaces</code></pre>
            <script>
                const x = "preserve   me";
            </script>
        </div>
    </body>
</html>"""
        minified = minify_html(sample)
        self.assertTrue(minified.startswith("<!DOCTYPE html>"))
        self.assertNotIn("<!-- Test Comment -->", minified)
        self.assertIn("<pre><code>code block preserves   spaces</code></pre>", minified)
        self.assertIn('const x = "preserve   me";', minified)
        self.assertIn(".test { color: red; }", minified)
        # Verify no empty lines
        self.assertNotIn("\n\n", minified)

    def test_generate_thumbnails_and_render(self):
        if not HAS_PIL:
            self.skipTest("PIL not available")
        from PIL import Image

        with tempfile.TemporaryDirectory() as td:
            # Create a test 800x600 image
            img_path = os.path.join(td, "test.jpg")
            im = Image.new("RGB", (800, 600), color=(255, 0, 0))
            im.save(img_path)

            created = generate_thumbnails(td, max_size=(200, 200))
            self.assertEqual(created, 1)

            thumbs_dir = os.path.join(td, ".thumbs")
            self.assertTrue(os.path.isdir(thumbs_dir))
            thumb_file = os.path.join(thumbs_dir, "test.jpg")
            self.assertTrue(os.path.isfile(thumb_file))

            # Verify render_attachment uses thumbnail and sets data-full
            html_snippet = render_attachment("test.jpg", td)
            self.assertIn('.thumbs/test.jpg', html_snippet)
            self.assertIn('data-full=', html_snippet)

            # Re-running thumbnail generation should skip existing
            created_again = generate_thumbnails(td, max_size=(200, 200))
            self.assertEqual(created_again, 0)

    def test_granular_media_filters_and_timeline_scrubber(self):
        messages = [
            {"date": "15/10/24 10:00:00", "sender": "Alice", "content": "Visite https://google.com pour voir", "dt": datetime(2024, 10, 15, 10, 0, 0)},
            {"date": "15/10/24 10:01:00", "sender": "Alice", "content": "Photo : pièce jointe : snap.jpg", "dt": datetime(2024, 10, 15, 10, 1, 0)},
            {"date": "15/10/24 10:02:00", "sender": "Bob", "content": "Vocal : pièce jointe : note.opus", "dt": datetime(2024, 10, 15, 10, 2, 0)},
            {"date": "16/10/24 09:00:00", "sender": "Bob", "content": "Doc : pièce jointe : fiche.pdf", "dt": datetime(2024, 10, 16, 9, 0, 0)},
            {"date": "16/10/24 09:05:00", "sender": "Alice", "content": "Vidéo : pièce jointe : film.mp4", "dt": datetime(2024, 10, 16, 9, 5, 0)},
        ]
        html_page = build_html(messages, "media", me_user="Alice")

        # Filter bar: granular media chips & date range
        self.assertIn('class="filter-media-chips"', html_page)
        for media_type in ("photo", "video", "audio", "doc", "link"):
            self.assertIn(f'data-type="{media_type}"', html_page)
        self.assertIn('id="filter-date-start"', html_page)
        self.assertIn('id="filter-date-end"', html_page)

        # Timeline scrubber element
        self.assertIn('id="timeline-scrubber"', html_page)
        self.assertIn('.scrubber-item', html_page)

        # Bubble attributes & types
        self.assertIn('data-media-types="link photo"', html_page)
        self.assertIn('data-media-type="photo"', html_page)
        self.assertIn('data-media-type="link"', html_page)
        self.assertIn('data-media-type="audio"', html_page)
        self.assertIn('data-media-type="doc"', html_page)
        self.assertIn('data-media-type="video"', html_page)

        # Read receipt double checkmarks for is-me
        self.assertIn('class="msg-status"', html_page)
        self.assertIn('✓✓', html_page)


if __name__ == "__main__":
    unittest.main()


