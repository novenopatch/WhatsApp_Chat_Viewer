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
from src.server import (
    WhatsAppViewerHandler,
    SESSIONS,
    extract_boundary,
    parse_multipart_stream,
    get_session_base_dir,
    cleanup_stale_sessions,
)


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

    def test_extract_boundary(self):
        """Should correctly extract boundary from various Content-Type header formats."""
        self.assertEqual(extract_boundary("multipart/form-data; boundary=xyz123"), "xyz123")
        self.assertEqual(extract_boundary('multipart/form-data; boundary="quoted_boundary"'), "quoted_boundary")
        self.assertEqual(extract_boundary("multipart/form-data; charset=utf-8; boundary=xyz"), "xyz")
        self.assertIsNone(extract_boundary("application/json"))
        self.assertIsNone(extract_boundary(""))

    def test_parse_multipart_stream(self):
        """Stream parser must write file directly to disk without memory buffering."""
        boundary = "BoundaryStreamingTest"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="me"\r\n\r\n'
            f"Alice\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="zip_file"; filename="test_upload.zip"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
            f"BINARY_DATA_FOR_STREAMING_TEST\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="standalone"\r\n\r\n'
            f"false\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        stream = io.BytesIO(body)
        fields, fpath, fname, fsize = parse_multipart_stream(
            stream,
            len(body),
            boundary,
            self.test_dir,
            chunk_size=16,
        )

        self.assertEqual(fields.get("me"), "Alice")
        self.assertEqual(fields.get("standalone"), "false")
        self.assertEqual(fname, "test_upload.zip")
        self.assertIsNotNone(fpath)
        self.assertTrue(os.path.isfile(fpath))
        with open(fpath, "rb") as f:
            self.assertEqual(f.read(), b"BINARY_DATA_FOR_STREAMING_TEST")

    def test_session_base_dir_and_cleanup(self):
        """Must return valid disk directory and cleanup stale wa_session folders."""
        base_dir = get_session_base_dir()
        self.assertTrue(os.path.isdir(base_dir))

        # Create dummy old session dir
        dummy = os.path.join(base_dir, "wa_session_dummy_to_clean")
        os.makedirs(dummy, exist_ok=True)
        self.assertTrue(os.path.isdir(dummy))

        cleanup_stale_sessions()
        self.assertFalse(os.path.exists(dummy))

    def test_server_media_serving_and_range_requests(self):
        """Server must serve media files under /media/{session_id}/ and support HTTP Range."""
        zip_path = os.path.join(self.test_dir, "media_chat.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "[15/10/2024 10:00:00] Bob: <pièce jointe : test_photo.jpg>\n")
            zf.writestr("test_photo.jpg", b"\xFF\xD8\xFF\xE0" + b"A" * 100)

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        boundary = "----MediaTestBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="zip_file"; filename="media_chat.zip"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8") + zip_bytes + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="standalone"\r\n\r\n'
            f"false\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/convert",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        session_id = json.loads(resp.read().decode("utf-8"))["session_id"]

        # View must contain /media/{session_id}/test_photo.jpg
        view_url = f"http://127.0.0.1:{self.port}/view/{session_id}"
        view_html = urllib.request.urlopen(view_url).read().decode("utf-8")
        self.assertIn(f"/media/{session_id}/test_photo.jpg", view_html)

        # Direct media request: GET /media/{session_id}/test_photo.jpg
        media_url = f"http://127.0.0.1:{self.port}/media/{session_id}/test_photo.jpg"
        media_resp = urllib.request.urlopen(media_url)
        self.assertEqual(media_resp.status, 200)
        self.assertEqual(media_resp.headers.get("Content-Type"), "image/jpeg")
        self.assertEqual(media_resp.headers.get("Accept-Ranges"), "bytes")
        content = media_resp.read()
        self.assertTrue(content.startswith(b"\xFF\xD8\xFF\xE0"))

        # HTTP Range request (for audio/video seeking)
        range_req = urllib.request.Request(media_url, headers={"Range": "bytes=0-3"})
        range_resp = urllib.request.urlopen(range_req)
        self.assertEqual(range_resp.status, 206)
        self.assertEqual(range_resp.headers.get("Content-Range"), "bytes 0-3/104")
        self.assertEqual(range_resp.read(), b"\xFF\xD8\xFF\xE0")

        # Resilient fallback: GET /view/test_photo.jpg
        fallback_url = f"http://127.0.0.1:{self.port}/view/test_photo.jpg"
        fallback_resp = urllib.request.urlopen(fallback_url)
        self.assertEqual(fallback_resp.status, 200)
        self.assertTrue(fallback_resp.read().startswith(b"\xFF\xD8\xFF\xE0"))


if __name__ == "__main__":
    unittest.main()
