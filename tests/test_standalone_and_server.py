"""Unit tests for Standalone HTML mode, Print / PDF layout, and Web Server."""

import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
import http.server

from src.renderer import (
    to_base64_data_uri,
    render_attachment,
    _collect_gallery_data,
    build_html,
)
from src.server import WhatsAppViewerHandler, SESSIONS


class TestStandaloneAndServer(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), WhatsAppViewerHandler)
        self.port = self.server.server_address[1]
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.test_dir, ignore_errors=True)
        SESSIONS.clear()

    def test_to_base64_data_uri(self):
        """Must convert local media files to correct Base64 Data URIs."""
        img_path = os.path.join(self.test_dir, "test.jpg")
        with open(img_path, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0fakejpegdata")

        uri = to_base64_data_uri(img_path)
        self.assertIsNotNone(uri)
        self.assertTrue(uri.startswith("data:image/jpeg;base64,"))

        # Size limit test
        small_limit_uri = to_base64_data_uri(img_path, max_size=5)
        self.assertIsNone(small_limit_uri)

        # Missing file test
        self.assertIsNone(to_base64_data_uri("/path/does/not/exist.png"))

    def test_render_attachment_standalone(self):
        """Must embed image into HTML as data URI when standalone=True."""
        img_path = os.path.join(self.test_dir, "photo.png")
        with open(img_path, "wb") as f:
            f.write(b"\x89PNGfakeimage")

        html_snippet = render_attachment("photo.png", self.test_dir, standalone=True)
        self.assertIn("data:image/png;base64,", html_snippet)
        self.assertIn('class="media-img"', html_snippet)

    def test_build_html_standalone_and_print_layout(self):
        """Must embed all media and include print controls & print header in HTML."""
        img_path = os.path.join(self.test_dir, "photo.jpg")
        with open(img_path, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0fakejpeg")

        messages = [
            {
                "sender": "Alice",
                "date": "15/10/2024 10:00:00",
                "dt": None,
                "content": "<pièce jointe : photo.jpg>",
                "reactions": [],
            }
        ]

        output_path = os.path.join(self.test_dir, "out.html")
        html_out = build_html(
            messages,
            self.test_dir,
            output_path=output_path,
            standalone=True,
        )

        # Verify standalone Base64 embedding
        self.assertIn("data:image/jpeg;base64,", html_out)

        # Verify Print button and Print header
        self.assertIn('id="print-btn"', html_out)
        self.assertIn('class="print-header"', html_out)
        self.assertIn("window.print()", html_out)

    def test_server_index_get(self):
        """Server must serve Drag & Drop interface at GET /."""
        url = f"http://127.0.0.1:{self.port}/"
        resp = urllib.request.urlopen(url)
        self.assertEqual(resp.status, 200)
        content = resp.read().decode("utf-8")
        self.assertIn("WhatsApp Chat Viewer", content)
        self.assertIn("dropzone", content)

    def test_server_convert_api_and_view(self):
        """Server must process uploaded zip, generate session, and serve view."""
        # Create a sample WhatsApp ZIP
        zip_path = os.path.join(self.test_dir, "chat.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "[15/10/2024 10:00:00] Bob: Bonjour le monde !\n")

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        boundary = "----TestBoundary123"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="zip_file"; filename="chat.zip"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8") + zip_bytes + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="me"\r\n\r\n'
            f"Bob\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="standalone"\r\n\r\n'
            f"true\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/convert",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)

        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        session_id = data["session_id"]
        self.assertIn(session_id, SESSIONS)

        # Test GET /view/{session_id}
        view_url = f"http://127.0.0.1:{self.port}/view/{session_id}"
        view_resp = urllib.request.urlopen(view_url)
        self.assertEqual(view_resp.status, 200)
        view_html = view_resp.read().decode("utf-8")
        self.assertIn("Bonjour le monde", view_html)

        # Test GET /download/{session_id}
        down_url = f"http://127.0.0.1:{self.port}/download/{session_id}"
        down_resp = urllib.request.urlopen(down_url)
        self.assertEqual(down_resp.status, 200)
        self.assertIn("attachment", down_resp.headers.get("Content-Disposition", ""))

    def test_server_invalid_upload(self):
        """Server must return 400 when invalid zip is uploaded."""
        boundary = "----BadBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="zip_file"; filename="corrupt.zip"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
            f"not a zip file\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/convert",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
