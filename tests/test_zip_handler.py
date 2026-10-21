"""Unit tests for the WhatsApp ZIP export handler module."""

import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from src.zip_handler import (
    is_zip_file,
    safe_extract_zip,
    find_chat_in_extracted,
    extract_whatsapp_zip,
)
from src.config import parse_args, load_config


class TestZipHandler(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_is_zip_file(self):
        self.assertFalse(is_zip_file(None))
        self.assertFalse(is_zip_file(""))
        self.assertFalse(is_zip_file("/non/existent/path.zip"))
        self.assertFalse(is_zip_file(self.test_dir))

        # Text file
        txt_file = os.path.join(self.test_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("hello")
        self.assertFalse(is_zip_file(txt_file))

        # Real zip file
        zip_file = os.path.join(self.test_dir, "test.zip")
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("test.txt", "content")
        self.assertTrue(is_zip_file(zip_file))

    def test_safe_extract_zip_normal(self):
        zip_path = os.path.join(self.test_dir, "archive.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")
            zf.writestr("photo.jpg", b"fake_jpeg_bytes")

        extract_target = os.path.join(self.test_dir, "extracted")
        files = safe_extract_zip(zip_path, extract_target)

        self.assertEqual(len(files), 2)
        self.assertTrue(os.path.isfile(os.path.join(extract_target, "_chat.txt")))
        self.assertTrue(os.path.isfile(os.path.join(extract_target, "photo.jpg")))

    def test_safe_extract_zip_slip_protection(self):
        """Must reject members attempting to write outside target directory (Zip Slip)."""
        zip_path = os.path.join(self.test_dir, "malicious.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Create a ZipInfo with ../ path traversal
            bad_member = zipfile.ZipInfo("../evil.txt")
            zf.writestr(bad_member, "evil content")

        extract_target = os.path.join(self.test_dir, "safe_folder")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target)
        self.assertIn("Zip Slip", str(ctx.exception))

    def test_find_chat_in_extracted_ios_format(self):
        """iOS export: _chat.txt + media at root."""
        extract_dir = os.path.join(self.test_dir, "ios_extracted")
        os.makedirs(extract_dir, exist_ok=True)
        chat_path = os.path.join(extract_dir, "_chat.txt")
        with open(chat_path, "w", encoding="utf-8") as f:
            f.write("15/10/24 10:00 - Alice: Coucou")
        with open(os.path.join(extract_dir, "image.jpg"), "w") as f:
            f.write("fake")

        found_chat, found_media = find_chat_in_extracted(extract_dir)
        self.assertEqual(os.path.abspath(found_chat), os.path.abspath(chat_path))
        self.assertEqual(os.path.abspath(found_media), os.path.abspath(extract_dir))

    def test_find_chat_in_extracted_android_format(self):
        """Android export: WhatsApp Chat - Alice.txt with subfolder or media folder."""
        extract_dir = os.path.join(self.test_dir, "android_extracted")
        media_subdir = os.path.join(extract_dir, "media")
        os.makedirs(media_subdir, exist_ok=True)
        chat_path = os.path.join(extract_dir, "WhatsApp Chat with Bob.txt")
        with open(chat_path, "w", encoding="utf-8") as f:
            f.write("15/10/2024, 10:00 - Bob: Hello")
        with open(os.path.join(media_subdir, "note.opus"), "w") as f:
            f.write("voice")

        found_chat, found_media = find_chat_in_extracted(extract_dir)
        self.assertEqual(os.path.abspath(found_chat), os.path.abspath(chat_path))
        self.assertEqual(os.path.abspath(found_media), os.path.abspath(media_subdir))

    def test_find_chat_in_extracted_content_heuristics(self):
        """Non-standard filename but containing valid WhatsApp messages."""
        extract_dir = os.path.join(self.test_dir, "heuristic_extracted")
        os.makedirs(extract_dir, exist_ok=True)
        chat_path = os.path.join(extract_dir, "discussion_exportée.txt")
        with open(chat_path, "w", encoding="utf-8") as f:
            f.write("[15/10/2024 10:00:00] Alice: Salut tout le monde\n")

        found_chat, _ = find_chat_in_extracted(extract_dir)
        self.assertEqual(os.path.abspath(found_chat), os.path.abspath(chat_path))

    def test_find_chat_in_extracted_not_found(self):
        extract_dir = os.path.join(self.test_dir, "empty_extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with self.assertRaises(FileNotFoundError):
            find_chat_in_extracted(extract_dir)

    def test_extract_whatsapp_zip_full(self):
        zip_path = os.path.join(self.test_dir, "export_full.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")
            zf.writestr("photo.jpg", b"123")

        chat_file, media_dir = extract_whatsapp_zip(zip_path)
        self.assertTrue(os.path.isfile(chat_file))
        self.assertTrue(os.path.isdir(media_dir))
        self.assertEqual(os.path.basename(chat_file), "_chat.txt")

    def test_load_config_with_zip_flag(self):
        zip_path = os.path.join(self.test_dir, "cli_flag.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")

        chat, media, output, me, _ = load_config(["--zip", zip_path, "--output", "out.html"])
        self.assertTrue(os.path.isfile(chat))
        self.assertEqual(os.path.basename(chat), "_chat.txt")
        self.assertEqual(output, "out.html")

    def test_load_config_with_positional_zip(self):
        zip_path = os.path.join(self.test_dir, "positional.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")

        chat, media, output, me, _ = load_config([zip_path])
        self.assertTrue(os.path.isfile(chat))
        self.assertEqual(os.path.basename(chat), "_chat.txt")

    def test_load_config_with_chat_flag_pointing_to_zip(self):
        zip_path = os.path.join(self.test_dir, "as_chat.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")

        chat, media, output, me, _ = load_config(["--chat", zip_path])
        self.assertTrue(os.path.isfile(chat))

    def test_load_config_with_dir_flag_pointing_to_zip(self):
        zip_path = os.path.join(self.test_dir, "as_dir.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")

        chat, media, output, me, _ = load_config(["--dir", zip_path])
        self.assertTrue(os.path.isfile(chat))

    def test_load_config_from_dotenv_zip(self):
        zip_path = os.path.join(self.test_dir, "env_archive.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")

        dotenv_file = os.path.join(self.test_dir, ".env")
        with open(dotenv_file, "w") as f:
            f.write(f"ZIP_FILE={zip_path}\nME=Alice\n")

        orig_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            chat, media, output, me, _ = load_config([])
            self.assertTrue(os.path.isfile(chat))
            self.assertEqual(me, "Alice")
        finally:
            os.chdir(orig_cwd)

    def test_zip_bomb_file_count_limit(self):
        """Must reject archives with an excessive number of files (file count bomb)."""
        zip_path = os.path.join(self.test_dir, "many_files.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(15):
                zf.writestr(f"file_{i}.txt", "data")

        extract_target = os.path.join(self.test_dir, "too_many_extracted")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target, max_files=10)
        self.assertIn("nombre excessif de fichiers", str(ctx.exception))

    def test_zip_bomb_declared_size_limit(self):
        """Must reject archives whose declared uncompressed size exceeds max_total_size."""
        zip_path = os.path.join(self.test_dir, "huge_declared.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Create a file with 10 KB content
            zf.writestr("big.bin", b"X" * 10240)

        extract_target = os.path.join(self.test_dir, "huge_extracted")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target, max_total_size=5000)
        self.assertIn("taille totale déclarée excessive", str(ctx.exception))

    def test_zip_bomb_compression_ratio_limit(self):
        """Must reject archives with abnormal compression ratio on large files."""
        zip_path = os.path.join(self.test_dir, "high_ratio.zip")
        # 12 MB of identical zeros compress into a few KB
        zero_data = b"\x00" * (12 * 1024 * 1024)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("zeros.bin", zero_data)

        extract_target = os.path.join(self.test_dir, "ratio_extracted")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target, max_ratio=20.0, max_total_size=50 * 1024 * 1024)
        self.assertIn("ratio de compression anormal", str(ctx.exception))

    def test_zip_bomb_streaming_size_guard(self):
        """Must abort in real-time when actual decompressed bytes exceed limit, and clean up."""
        zip_path = os.path.join(self.test_dir, "streaming_bomb.zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 500 KB of text
            zf.writestr("expand.txt", b"A" * (500 * 1024))

        extract_target = os.path.join(self.test_dir, "streaming_target")
        with self.assertRaises(ValueError) as ctx:
            # Allowed total size only 20 KB
            safe_extract_zip(zip_path, extract_target, max_total_size=20 * 1024)
        self.assertIn("bombe zip", str(ctx.exception))
        # Ensure partial file was cleaned up
        target_file = os.path.join(extract_target, "expand.txt")
        self.assertFalse(os.path.exists(target_file))

    def test_empty_zip_rejection(self):
        """Must reject completely empty 0-byte zip file."""
        zip_path = os.path.join(self.test_dir, "empty.zip")
        with open(zip_path, "wb") as f:
            pass
        extract_target = os.path.join(self.test_dir, "empty_target")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target)
        self.assertIn("archive ZIP vide", str(ctx.exception))

    def test_zip_bomb_overlapping_headers(self):
        """Must detect non-recursive zip bombs with duplicated local header offsets."""
        import io, struct
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("file1.txt", b"A" * 100)

        raw = buf.getvalue()
        eocd_pos = raw.rfind(b"PK\x05\x06")
        cd_size = struct.unpack("<I", raw[eocd_pos + 12 : eocd_pos + 16])[0]
        cd_offset = struct.unpack("<I", raw[eocd_pos + 16 : eocd_pos + 20])[0]
        cd_data = raw[cd_offset : cd_offset + cd_size]

        cd_entry2 = bytearray(cd_data)
        cd_entry2[46 : 46 + 9] = b"file2.txt"

        new_zip = bytearray(raw[:cd_offset] + cd_data + bytes(cd_entry2) + raw[eocd_pos:])
        new_eocd = len(new_zip) - 22
        struct.pack_into("<H", new_zip, new_eocd + 8, 2)
        struct.pack_into("<H", new_zip, new_eocd + 10, 2)
        struct.pack_into("<I", new_zip, new_eocd + 12, cd_size * 2)

        zip_path = os.path.join(self.test_dir, "overlapping.zip")
        with open(zip_path, "wb") as f:
            f.write(new_zip)

        extract_target = os.path.join(self.test_dir, "overlap_target")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target)
        self.assertIn("en-têtes locaux dupliqués", str(ctx.exception))

    def test_rejection_of_symlinks_in_zip(self):
        """Must reject zip archives containing symbolic link entries."""
        zip_path = os.path.join(self.test_dir, "symlink.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            info = zipfile.ZipInfo("bad_link")
            info.create_system = 3  # Unix
            info.external_attr = 0o120777 << 16  # Symlink attribute
            zf.writestr(info, "/etc/passwd")

        extract_target = os.path.join(self.test_dir, "symlink_target")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target)
        self.assertIn("lien symbolique interdit", str(ctx.exception))

    def test_rejection_of_null_bytes_and_colons(self):
        """Must reject files with null bytes or colons in their paths."""
        zip_path = os.path.join(self.test_dir, "colon.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test:stream.txt", "content")

        extract_target = os.path.join(self.test_dir, "colon_target")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target)
        self.assertIn("caractère deux-points interdit", str(ctx.exception))

    def test_rejection_of_windows_reserved_names(self):
        """Must reject Windows reserved device names like AUX, CON, NUL, COM1."""
        zip_path = os.path.join(self.test_dir, "win_dev.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("aux.txt", "malicious device file")

        extract_target = os.path.join(self.test_dir, "win_dev_target")
        with self.assertRaises(ValueError) as ctx:
            safe_extract_zip(zip_path, extract_target)
        self.assertIn("nom de périphérique réservé Windows interdit", str(ctx.exception))

    def test_rejection_of_existing_symlink_traversal(self):
        """Must reject writing into target if a symlink exists pointing outside."""
        outside_dir = tempfile.mkdtemp()
        try:
            extract_target = os.path.join(self.test_dir, "symlink_dest")
            os.makedirs(extract_target, exist_ok=True)
            # Create symlink inside extract_target pointing outside
            symlink_sub = os.path.join(extract_target, "escape")
            os.symlink(outside_dir, symlink_sub)

            zip_path = os.path.join(self.test_dir, "traverse.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("escape/pwned.txt", "payload")

            with self.assertRaises(ValueError) as ctx:
                safe_extract_zip(zip_path, extract_target)
            self.assertIn("lien symbolique", str(ctx.exception))
            self.assertFalse(os.path.exists(os.path.join(outside_dir, "pwned.txt")))
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_disk_space_precheck_failure(self):
        """Must raise an OSError if available disk space is insufficient."""
        zip_path = os.path.join(self.test_dir, "disk_test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")

        extract_target = os.path.join(self.test_dir, "disk_target")
        with patch("shutil.disk_usage") as mock_usage:
            # Simulate only 10 KB free on disk
            mock_usage.return_value = type("Usage", (), {"free": 10 * 1024})()
            with self.assertRaises(OSError) as ctx:
                safe_extract_zip(zip_path, extract_target)
            self.assertIn("Espace disque insuffisant", str(ctx.exception))

    def test_unicode_filename_physical_offset_check(self):
        """Must not raise false positive overlap error when UTF-8 length exceeds ASCII length."""
        zip_path = os.path.join(self.test_dir, "unicode_names.zip")
        unicode_name = "00027898-≡¥æë≡¥æû≡¥æí≡¥æÄ ≡¥É║≡¥æÖ≡¥æ£≡¥æñ.vcf"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "15/10/24 10:00 - Alice: Salut")
            zf.writestr(unicode_name, "BEGIN:VCARD\nVERSION:3.0\nEND:VCARD\n")
            zf.writestr("00027916-photo.jpg", b"\xFF\xD8\xFF\xE0" + b"0" * 50)

        extract_target = os.path.join(self.test_dir, "unicode_target")
        extracted = safe_extract_zip(zip_path, extract_target)
        self.assertEqual(len(extracted), 3)


if __name__ == "__main__":
    unittest.main()
