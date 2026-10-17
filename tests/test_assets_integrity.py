"""Integrity tests for static assets (templates, CSS, and JS).

Prevents accidental deletion, typo in placeholders, or missing required UI components
when editing template files.
"""

import unittest
from src.renderer import load_template_file


class TestAssetsIntegrity(unittest.TestCase):

    def test_template_files_exist_and_non_empty(self):
        for name in ("base.html", "style.css", "app.js"):
            content = load_template_file(name)
            self.assertTrue(len(content) > 100, f"Template {name} is suspiciously small or empty!")

    def test_base_html_has_all_placeholders(self):
        required_placeholders = [
            "{{ title }}",
            "{{ style }}",
            "{{ initial_me }}",
            "{{ chat_label }}",
            "{{ attendees_header }}",
            "{{ start_date }}",
            "{{ end_date }}",
            "{{ me_options_html }}",
            "{{ legend_items }}",
            "{{ grouped_html }}",
            "{{ stats_html }}",
            "{{ script }}",
            "{{ gallery_data }}",
            "{{ media_count }}",
        ]
        base_html = load_template_file("base.html")
        for placeholder in required_placeholders:
            self.assertIn(placeholder, base_html, f"Missing placeholder {placeholder} in base.html!")

    def test_base_html_has_essential_dom_elements(self):
        required_ids = [
            'id="search-input"',
            'id="search-count"',
            'id="search-prev"',
            'id="search-next"',
            'id="theme-toggle"',
            'id="me-select"',
            'id="chat-container"',
            'id="lightbox"',
            'id="scroll-btns"',
            'id="gallery-btn"',
            'id="gallery-modal"',
            'id="wallpaper-toggle"',
            'id="filter-sender"',
            'id="filter-month"',
            'id="filter-media-only"',
            'id="filter-reset"',
        ]
        base_html = load_template_file("base.html")
        for dom_id in required_ids:
            self.assertIn(dom_id, base_html, f"Missing required DOM element {dom_id} in base.html!")

    def test_css_has_performance_and_theme_rules(self):
        css = load_template_file("style.css")
        # Performance rules
        self.assertIn("content-visibility: auto", css)
        self.assertIn("contain-intrinsic-size", css)
        # Theme variables
        self.assertIn("--bg-body", css)
        self.assertIn("--bubble-sent-bg", css)
        self.assertIn("--bubble-received-bg", css)
        self.assertIn("body.dark-mode", css)
        self.assertIn("@media (prefers-color-scheme: dark)", css)
        # Print rule
        self.assertIn("@media print", css)

    def test_js_has_critical_functions(self):
        js = load_template_file("app.js")
        critical_symbols = [
            "debounce",
            "runSearch",
            "clearSearch",
            "goToMatch",
            "attachImageListeners",
            "openLightbox",
            "closeLightbox",
            "toggleAudioSpeed",
            "applyTheme",
            "setMeUser",
            "openGallery",
            "closeGallery",
            "jumpToMessage",
            "applyFilters",
        ]
        for sym in critical_symbols:
            self.assertIn(sym, js, f"Missing critical JavaScript function/symbol '{sym}' in app.js!")




if __name__ == "__main__":
    unittest.main()
