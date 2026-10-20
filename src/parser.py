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
    QUOTE_LINE_PATTERN,
    QUOTE_AUTHOR_PATTERN,
    EMOJI_PATTERN,
    REACTION_LINE_PATTERN,
    TRAILING_REACTION_PATTERN,
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


def format_inline_markdown(text: str) -> str:
    """Convert raw inline text to safe HTML with markdown & clickable URLs."""
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
            esc = WA_MONO.sub(r"<code>\1</code>", esc)
            esc = WA_BOLD.sub(r"<strong>\1</strong>", esc)
            esc = WA_ITALIC.sub(r"<em>\1</em>", esc)
            esc = WA_STRIKE.sub(r"<del>\1</del>", esc)
            result.append(esc)
    return "".join(result)


def format_message(text: str, quote_target_id: str | None = None) -> str:
    """Convert raw WhatsApp message text to safe HTML with markdown, quotes & clickable URLs."""
    code_blocks: list[str] = []

    def save_code_block(match: re.Match) -> str:
        idx = len(code_blocks)
        esc_code = html.escape(match.group(1))
        code_blocks.append(f"<pre><code>{esc_code}</code></pre>")
        return f"@@WACODEBLOCK{idx}@@"

    text_no_blocks = WA_CODE_BLOCK.sub(save_code_block, text)

    lines = text_no_blocks.split("\n")
    blocks: list[tuple[str, list[str]]] = []
    current_lines: list[str] = []
    in_quote = False

    for line in lines:
        m = QUOTE_LINE_PATTERN.match(line)
        if m:
            if not in_quote and current_lines:
                blocks.append(("text", current_lines))
                current_lines = []
            in_quote = True
            current_lines.append(m.group(1))
        else:
            if in_quote and current_lines:
                blocks.append(("quote", current_lines))
                current_lines = []
            in_quote = False
            current_lines.append(line)

    if current_lines:
        blocks.append(("quote" if in_quote else "text", current_lines))

    has_quotes = any(b[0] == "quote" for b in blocks)
    rendered_blocks: list[str] = []

    for btype, blines in blocks:
        if btype == "quote":
            first_line = blines[0]
            author_match = QUOTE_AUTHOR_PATTERN.match(first_line)
            if author_match:
                author = (author_match.group(1) or author_match.group(2)).strip()
                first_content = author_match.group(3)
                rest = blines[1:]
                quote_text_lines = ([first_content] if first_content else []) + rest
            else:
                author = ""
                quote_text_lines = blines

            formatted_quote_body = "<br>".join(format_inline_markdown(ql) for ql in quote_text_lines)
            author_html = f'<div class="wa-quote-author">{html.escape(author)}</div>' if author else ""
            author_attr = f' data-quoted-author="{html.escape(author)}"' if author else ""
            target_attr = f' data-target-id="{html.escape(quote_target_id)}"' if quote_target_id else ""
            rendered_blocks.append(
                f'<div class="wa-quote-box"{author_attr}{target_attr}>'
                f'<div class="wa-quote-accent"></div>'
                f'<div class="wa-quote-content">{author_html}'
                f'<div class="wa-quote-text">{formatted_quote_body}</div></div></div>'
            )
        else:
            formatted_text = "<br>".join(format_inline_markdown(tl) for tl in blines)
            if formatted_text:
                rendered_blocks.append(formatted_text)

    result = "".join(rendered_blocks) if has_quotes else "<br>".join(rendered_blocks)

    for idx, cb in enumerate(code_blocks):
        result = result.replace(f"@@WACODEBLOCK{idx}@@", cb)

    return result


def parse_reaction_notification(content: str) -> tuple[str, str] | None:
    """Detect if content is a WhatsApp reaction notification to a prior message."""
    clean = content.strip("\u200e\u202f ")
    m = REACTION_LINE_PATTERN.match(clean)
    if m:
        emoji, snippet = m.groups()
        return emoji.strip(), snippet.strip()
    return None


def extract_trailing_reactions(content: str, sender: str = "") -> tuple[str, list[dict]]:
    """Extract and remove trailing reaction tags from message content.

    Returns:
        (cleaned_content, list_of_reactions)
    """
    m = TRAILING_REACTION_PATTERN.search(content)
    if not m:
        return content, []

    reactions: list[dict] = []
    g1, g2, g3 = m.groups()
    if g1:
        parts = [p.strip() for p in g1.split(",") if p.strip()]
        for part in parts:
            emojis = EMOJI_PATTERN.findall(part)
            if emojis:
                emoji = emojis[0]
                r_sender = part.replace(emoji, "").strip() or sender
                reactions.append({"emoji": emoji, "sender": r_sender})
    else:
        raw_emojis = g2 or g3 or ""
        emojis = EMOJI_PATTERN.findall(raw_emojis)
        for emoji in emojis:
            reactions.append({"emoji": emoji, "sender": sender})

    cleaned = content[:m.start()] + content[m.end():]
    return cleaned.rstrip(), reactions


def resolve_quote_target_id(messages: list[dict], current_idx: int, content: str) -> str | None:
    """Find the ID of the earlier message referenced in a quote block, if any."""
    lines = content.split("\n")
    quote_first_line = None
    for line in lines:
        m = QUOTE_LINE_PATTERN.match(line)
        if m:
            quote_first_line = m.group(1).strip()
            break

    if not quote_first_line:
        return None

    author_match = QUOTE_AUTHOR_PATTERN.match(quote_first_line)
    quoted_author = (author_match.group(1) or author_match.group(2)).strip() if author_match else None
    snippet = author_match.group(3).strip() if author_match else quote_first_line

    if not snippet:
        return None

    for prev_idx in range(current_idx - 1, -1, -1):
        prev = messages[prev_idx]
        if prev.get("is_reaction_event"):
            continue
        if quoted_author and prev.get("sender", "").strip().lower() != quoted_author.lower():
            continue
        prev_content = prev.get("content", "")
        if snippet.lower() in prev_content.lower() or prev_content.lower() in snippet.lower():
            return f"msg-{prev_idx}"

    return None


def process_chat_reactions(messages: list[dict]) -> list[dict]:
    """Link reactions to previous messages and extract trailing reactions."""
    for idx, msg in enumerate(messages):
        # 1. Trailing reactions
        msg_content = msg.get("content", "")
        cleaned, trailing = extract_trailing_reactions(msg_content, sender=msg.get("sender", ""))
        if trailing:
            msg["content"] = cleaned
            msg.setdefault("reactions", []).extend(trailing)

        # 2. Reaction notification lines
        react_info = parse_reaction_notification(msg["content"])
        if react_info:
            emoji, target_snippet = react_info
            target_found = False
            for prev_idx in range(idx - 1, -1, -1):
                prev_msg = messages[prev_idx]
                if prev_msg.get("is_reaction_event"):
                    continue
                prev_content = prev_msg.get("content", "")
                if target_snippet.lower() in prev_content.lower() or prev_content.lower() in target_snippet.lower():
                    prev_msg.setdefault("reactions", []).append({
                        "emoji": emoji,
                        "sender": msg["sender"],
                    })
                    msg["is_reaction_event"] = True
                    msg["reaction_target_id"] = f"msg-{prev_idx}"
                    target_found = True
                    break
            if not target_found:
                msg["is_reaction_event"] = False

    return messages


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
    """Parse a WhatsApp exported .txt file into a list of message dicts with resolved reactions."""
    raw_messages = list(iter_chat(file_path))
    return process_chat_reactions(raw_messages)
