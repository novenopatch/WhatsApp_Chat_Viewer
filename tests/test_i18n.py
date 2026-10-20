"""Unit tests for the Internationalisation (i18n) module."""

import unittest
from datetime import datetime
from src.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_translations,
    get_day_names,
    get_month_names,
    get_system_icons,
    get_media_type_map,
    detect_system_language,
    resolve_language,
)
from src.parser import format_day_label, get_media_type_label
from src.renderer import build_html
from src.config import parse_args


class TestI18n(unittest.TestCase):
    """Test suite for multilingual functionality."""

    def test_default_language_is_english(self):
        """Ensure primary language of the library is English."""
        self.assertEqual(DEFAULT_LANGUAGE, "en")
        self.assertIn("en", SUPPORTED_LANGUAGES)
        self.assertIn("fr", SUPPORTED_LANGUAGES)

    def test_get_translations_english(self):
        t_en = get_translations("en")
        self.assertEqual(t_en["search_placeholder"], "Search…")
        self.assertEqual(t_en["date_from"], "From")
        self.assertEqual(t_en["date_to"], "to")
        self.assertEqual(t_en["js_locale"], "en-GB")
        self.assertEqual(t_en["chat_label"], "WhatsApp Conversation")
        self.assertEqual(t_en["edited_badge"], "edited")

    def test_get_translations_french(self):
        t_fr = get_translations("fr")
        self.assertEqual(t_fr["search_placeholder"], "Rechercher…")
        self.assertEqual(t_fr["date_from"], "Du")
        self.assertEqual(t_fr["date_to"], "au")
        self.assertEqual(t_fr["js_locale"], "fr-FR")
        self.assertEqual(t_fr["chat_label"], "Conversation WhatsApp")
        self.assertEqual(t_fr["edited_badge"], "modifié")

    def test_get_translations_unknown_fallback(self):
        """Unknown languages should cleanly fall back to English default."""
        t_unknown = get_translations("es")
        self.assertEqual(t_unknown["search_placeholder"], "Search…")

    def test_day_names(self):
        days_en = get_day_names("en")
        self.assertEqual(len(days_en), 7)
        self.assertEqual(days_en[0], "Monday")
        self.assertEqual(days_en[6], "Sunday")

        days_fr = get_day_names("fr")
        self.assertEqual(len(days_fr), 7)
        self.assertEqual(days_fr[0], "Lundi")
        self.assertEqual(days_fr[6], "Dimanche")

    def test_month_names(self):
        months_en = get_month_names("en")
        self.assertEqual(len(months_en), 13)
        self.assertEqual(months_en[1], "January")
        self.assertEqual(months_en[12], "December")

        months_fr = get_month_names("fr")
        self.assertEqual(len(months_fr), 13)
        self.assertEqual(months_fr[1], "janvier")
        self.assertEqual(months_fr[12], "décembre")

    def test_system_icons(self):
        icons_en = get_system_icons("en")
        self.assertEqual(icons_en["voice call"], "📞")
        self.assertEqual(icons_en["encrypt"], "🔒")

        icons_fr = get_system_icons("fr")
        self.assertEqual(icons_fr["appel vocal"], "📞")
        self.assertEqual(icons_fr["chiffr"], "🔒")

    def test_media_type_map(self):
        media_en = get_media_type_map("en")
        self.assertEqual(media_en["VIDEO"], "🎬 Video")

        media_fr = get_media_type_map("fr")
        self.assertEqual(media_fr["VIDEO"], "🎬 Vidéo")

    def test_format_day_label_i18n(self):
        dt = datetime(2025, 12, 25)  # Thursday
        self.assertEqual(format_day_label(dt, lang="en"), "Thursday 25 December 2025")
        self.assertEqual(format_day_label(dt, lang="fr"), "Jeudi 25 décembre 2025")

    def test_get_media_type_label_i18n(self):
        self.assertEqual(get_media_type_label("video.mp4", lang="en"), "🎬 Video")
        self.assertEqual(get_media_type_label("video.mp4", lang="fr"), "🎬 Vidéo")

    def test_build_html_multilingual_output(self):
        sample_msgs = [
            {
                "date": "20/10/24 14:00:00",
                "sender": "Alice",
                "content": "Hello world",
                "dt": datetime(2024, 10, 20, 14, 0, 0),
            }
        ]

        # English (Default)
        html_en = build_html(sample_msgs, "media", lang="en")
        self.assertIn('<html lang="en">', html_en)
        self.assertIn('placeholder="Search…"', html_en)
        self.assertIn('title="Media gallery"', html_en)
        self.assertIn('Photos &amp; Videos', html_en)
        self.assertIn('"date_from": "From"', html_en)

        # French
        html_fr = build_html(sample_msgs, "media", lang="fr")
        self.assertIn('<html lang="fr">', html_fr)
        self.assertIn('placeholder="Rechercher…"', html_fr)
        self.assertIn('title="Galerie de médias"', html_fr)
        self.assertIn('Photos &amp; Vidéos', html_fr)
        self.assertIn('"date_from": "Du"', html_fr)

    def test_cli_lang_argument(self):
        args_en = parse_args(["--lang", "en"])
        self.assertEqual(args_en.lang, "en")

        args_fr = parse_args(["-l", "fr"])
        self.assertEqual(args_fr.lang, "fr")

        args_auto = parse_args(["--lang", "auto"])
        self.assertEqual(args_auto.lang, "auto")

        args_default = parse_args([])
        self.assertIsNone(args_default.lang)

    def test_detect_system_language(self):
        import os
        from unittest import mock

        # French system locale
        with mock.patch.dict(os.environ, {"LANG": "fr_FR.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(detect_system_language(), "fr")

        with mock.patch.dict(os.environ, {"LANG": "fr_CA.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(detect_system_language(), "fr")

        with mock.patch.dict(os.environ, {"LC_ALL": "fr", "LANG": "en_US.UTF-8"}):
            self.assertEqual(detect_system_language(), "fr")

        # English system locale
        with mock.patch.dict(os.environ, {"LANG": "en_US.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(detect_system_language(), "en")

        with mock.patch.dict(os.environ, {"LANG": "en_GB.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(detect_system_language(), "en")

        # Unsupported system language -> fallback to DEFAULT_LANGUAGE ('en')
        with mock.patch.dict(os.environ, {"LANG": "de_DE.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(detect_system_language(), "en")

    def test_resolve_language(self):
        import os
        from unittest import mock

        self.assertEqual(resolve_language("fr"), "fr")
        self.assertEqual(resolve_language("en"), "en")
        self.assertEqual(resolve_language("french"), "fr")
        self.assertEqual(resolve_language("es"), "en")  # unsupported -> fallback en

        # None or 'auto' resolves to detected system language
        with mock.patch.dict(os.environ, {"LANG": "fr_FR.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(resolve_language(None), "fr")
            self.assertEqual(resolve_language("auto"), "fr")

        with mock.patch.dict(os.environ, {"LANG": "en_US.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(resolve_language(None), "en")
            self.assertEqual(resolve_language("auto"), "en")

    def test_build_html_system_auto(self):
        import os
        from unittest import mock

        sample_msgs = [
            {
                "date": "20/10/24 14:00:00",
                "sender": "Alice",
                "content": "Bonjour",
                "dt": datetime(2024, 10, 20, 14, 0, 0),
            }
        ]

        # In French system environment, default build_html without lang argument produces French
        with mock.patch.dict(os.environ, {"LANG": "fr_FR.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            html_auto = build_html(sample_msgs, "media")
            self.assertIn('<html lang="fr">', html_auto)
            self.assertIn('placeholder="Rechercher…"', html_auto)

        # In English system environment, default build_html produces English
        with mock.patch.dict(os.environ, {"LANG": "en_US.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            html_auto = build_html(sample_msgs, "media")
            self.assertIn('<html lang="en">', html_auto)
            self.assertIn('placeholder="Search…"', html_auto)


if __name__ == "__main__":
    unittest.main()
