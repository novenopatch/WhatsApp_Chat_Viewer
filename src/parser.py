"""WhatsApp chat parser and text formatting utilities."""

import html
import os
from collections.abc import Iterator
from datetime import datetime
from src.constants import (
    MESSAGE_PATTERN,
    ATTACHMENT_KEYWORDS,
    DATE_FORMATS,
    FRENCH_MONTHS,
    SYSTEM_MESSAGE_PATTERN,
    SYSTEM_ICONS,
    MEDIA_TYPE_MAP,
    EDIT_ANNOTATION_PATTERN,
    DELETE_ANNOTATION_PATTERN,
    URL_PATTERN,
    WA_CODE_BLOCK,
    WA_MONO,
    WA_BOLD,
    WA_ITALIC,
    WA_STRIKE,
)


def parse_date(date_str: str) -> datetime | None:
    """Try to parse a WhatsApp date string into a datetime object."""
    clean_date = date_str.strip("\u200e\u202f ")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(clean_date, fmt)
        except ValueError:
            continue
    return None


def format_day_label(dt: datetime) -> str:
    """Return a human-readable French day label, e.g. 'Lundi 3 mars 2024'."""
    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return f"{day_names[dt.weekday()]} {dt.day} {FRENCH_MONTHS[dt.month]} {dt.year}"


def get_attachment_filename(raw_content: str) -> str | None:
    """Extract the filename from an attachment line, or return None if not an attachment."""
    for kw in ATTACHMENT_KEYWORDS:
        if kw in raw_content:
            part = raw_content.split(kw)[-1]
            return part.strip(" \u202a\u200e\u202c\u202f<>()")
    if "(file attached)" in raw_content:
        return raw_content.replace("(file attached)", "").strip(" \u202a\u200e\u202c\u202f<>()")
    return None


def is_system_message(content: str) -> bool:
    """Return True if this content is a WhatsApp system/event notification."""
    return bool(SYSTEM_MESSAGE_PATTERN.search(content))


def get_system_icon(content: str) -> str:
    """Return an appropriate emoji for a system message."""
    lower = content.lower()
    for keyword, icon in SYSTEM_ICONS.items():
        if keyword in lower:
            return icon
    return "ℹ️"


def get_media_type_label(filename: str) -> str:
    """Return a labeled media type string for a WhatsApp attachment filename."""
    parts = filename.split("-")
    if len(parts) >= 2:
        label = MEDIA_TYPE_MAP.get(parts[1].upper())
        if label:
            return label
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("jpg", "jpeg", "png", "gif"):
        return "📷 Photo"
    if ext in ("mp4", "mov", "3gp"):
        return "🎬 Vidéo"
    if ext in ("opus", "mp3", "ogg", "m4a", "aac"):
        return "🎤 Audio"
    if ext == "webp":
        return "🎭 Sticker"
    return "📎 Autre"


def format_message(text: str) -> str:
    """Convert raw WhatsApp message text to safe HTML with markdown & clickable URLs."""
    parts = URL_PATTERN.split(text)  # odd indices = URLs
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # URL
            esc = html.escape(part)
            result.append(
                f'<a href="{esc}" target="_blank" rel="noopener noreferrer">{esc}</a>'
            )
        else:
            esc = html.escape(part)
            # Apply WA markdown in order: code blocks, monospace, bold, italic, strikethrough
            esc = WA_CODE_BLOCK.sub(r"<pre><code>\1</code></pre>", esc)
            esc = WA_MONO.sub(r"<code>\1</code>", esc)
            esc = WA_BOLD.sub(r"<strong>\1</strong>", esc)
            esc = WA_ITALIC.sub(r"<em>\1</em>", esc)
            esc = WA_STRIKE.sub(r"<del>\1</del>", esc)
            result.append(esc)
    return "".join(result)


def strip_annotations(content: str) -> tuple[str, bool]:
    """Remove inline edit/delete markers from message content.

    Returns:
        (cleaned_content, was_edited)
    """
    was_edited = bool(EDIT_ANNOTATION_PATTERN.search(content))
    content = EDIT_ANNOTATION_PATTERN.sub("", content)
    content = DELETE_ANNOTATION_PATTERN.sub("", content)
    return content.strip(), was_edited


def iter_chat(file_path: str) -> Iterator[dict]:
    """Stream WhatsApp messages line-by-line from exported .txt without loading the full file into memory at once."""
    if not os.path.isfile(file_path):
        return

    current_msg = None
    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            match = MESSAGE_PATTERN.match(line)
            if match:
                if current_msg is not None:
                    yield current_msg
                date, sender, content = match.groups()
                current_msg = {
                    "date": date,
                    "sender": sender.strip(),
                    "content": content,
                    "dt": parse_date(date),
                }
            elif current_msg is not None:
                current_msg["content"] += "\n" + line

        if current_msg is not None:
            yield current_msg


def parse_chat(file_path: str) -> list[dict]:
    """Parse a WhatsApp exported .txt file into a list of message dicts."""
    return list(iter_chat(file_path))
