"""HTML generation and message rendering for WhatsApp conversations."""

import html
import json
import os
import re

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from src.constants import AVATAR_COLORS, URL_PATTERN
from src.parser import (
    format_day_label,
    is_system_message,
    get_system_icon,
    strip_annotations,
    get_attachment_filename,
    format_message,
)
from src.stats import compute_stats, render_stats_html
from src.user_detector import resolve_me_user


def generate_thumbnails(media_dir: str, max_size: tuple[int, int] = (400, 400), quality: int = 80) -> int:
    """Generate lightweight thumbnails in media_dir/.thumbs for image files.

    Skips files that already have an up-to-date thumbnail.
    Returns the count of new thumbnails created.
    """
    if not HAS_PIL or not media_dir or not os.path.isdir(media_dir):
        return 0

    thumbs_dir = os.path.join(media_dir, ".thumbs")
    try:
        os.makedirs(thumbs_dir, exist_ok=True)
    except OSError:
        return 0

    created = 0
    img_exts = (".jpg", ".jpeg", ".png")
    for fname in os.listdir(media_dir):
        if not fname.lower().endswith(img_exts):
            continue
        src_path = os.path.join(media_dir, fname)
        if not os.path.isfile(src_path):
            continue
        dst_path = os.path.join(thumbs_dir, fname)
        if os.path.isfile(dst_path):
            continue
        try:
            with Image.open(src_path) as im:
                im.thumbnail(max_size)
                if im.mode in ("RGBA", "P") and fname.lower().endswith((".jpg", ".jpeg")):
                    im = im.convert("RGB")
                im.save(dst_path, optimize=True, quality=quality)
                created += 1
        except Exception:
            continue
    return created


def _get_template_path(filename: str) -> str:
    """Return the absolute path to a template file."""
    return os.path.join(os.path.dirname(__file__), "templates", filename)


def load_template_file(filename: str) -> str:
    """Read and return content from a file in src/templates/."""
    path = _get_template_path(filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def render_attachment(filename: str, media_dir: str, output_dir: str = "") -> str:
    """Return the HTML snippet for a given attachment filename."""
    if output_dir:
        rel_media_dir = os.path.relpath(media_dir, output_dir).replace("\\", "/")
    else:
        rel_media_dir = media_dir.replace("\\", "/")

    filepath = f"{rel_media_dir}/{filename}".replace("//", "/")
    esc_filepath = html.escape(filepath, quote=True)
    parts = filename.split("-")

    file_type = parts[1].upper() if len(parts) >= 2 else ""

    if file_type == "STICKER":
        return f'<img src="{esc_filepath}" class="sticker-img" alt="Sticker" loading="lazy" decoding="async">'
    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
        thumb_disk_path = os.path.join(media_dir, ".thumbs", filename)
        if os.path.isfile(thumb_disk_path):
            thumb_filepath = f"{rel_media_dir}/.thumbs/{filename}".replace("//", "/")
            esc_thumb = html.escape(thumb_filepath, quote=True)
            return (
                f'<img src="{esc_thumb}" data-full="{esc_filepath}" '
                f'class="media-img" alt="Image" loading="lazy" decoding="async">'
            )
        return f'<img src="{esc_filepath}" class="media-img" alt="Image" loading="lazy" decoding="async">'
    if filename.lower().endswith(".webp"):
        return f'<img src="{esc_filepath}" class="sticker-img" alt="Sticker" loading="lazy" decoding="async">'
    if filename.lower().endswith((".mp4", ".mov", ".3gp")):
        return (
            f'<div class="video-container">'
            f'<video controls preload="none" class="media-video">'
            f'<source src="{esc_filepath}">Vidéo non supportée.</video>'
            f'<button type="button" class="video-fs-btn" title="Plein écran">⛶</button>'
            f'</div>'
        )
    if filename.lower().endswith((".opus", ".mp3", ".ogg", ".m4a", ".aac")):
        return (
            f'<div class="audio-container">'
            f'<audio controls preload="none" src="{esc_filepath}"></audio>'
            f'<button type="button" class="audio-speed-btn" title="Changer la vitesse (1x, 1.5x, 2x)">1x</button>'
            f'</div>'
        )
    if filename.lower().endswith(".pdf"):
        return f'<a href="{esc_filepath}" target="_blank">📄 {html.escape(filename)}</a>'
    return f'<a href="{esc_filepath}">📎 {html.escape(filename)}</a>'



def build_bubble(
    sender: str,
    color: str,
    initials: str,
    group_texts: list[str],
    is_me: bool = False,
    has_media: bool = False,
    month: str = "",
    media_types: str = "",
) -> str:
    """Build the HTML for a single message bubble (one sender, one or more sub-messages)."""
    avatar = (
        f'<div class="avatar" title="{html.escape(sender)}">'
        f'{html.escape(initials)}</div>'
    )
    sender_label = f'<div class="sender">{html.escape(sender)}</div>'
    me_class = " is-me" if is_me else ""
    media_attr = "true" if has_media else "false"
    month_attr = f' data-month="{html.escape(month)}"' if month else ""
    types_attr = f' data-media-types="{html.escape(media_types)}"' if media_types else ""
    return (
        f'<div class="message-row{me_class}" data-sender="{html.escape(sender)}" data-has-media="{media_attr}"{types_attr}{month_attr}>'
        f'{avatar}'
        f'<div class="message">{sender_label}{"".join(group_texts)}</div>'
        f'</div>'
    )



def _collect_gallery_data(
    messages: list[dict],
    media_dir: str,
    output_dir: str = "",
) -> dict:
    """Collect gallery items (photos, audios, docs, links) from parsed messages.

    Returns a dict with keys: photos, audios, docs, links.
    """
    if output_dir:
        rel_media = os.path.relpath(media_dir, output_dir).replace("\\", "/")
    else:
        rel_media = media_dir.replace("\\", "/")

    gallery_photos: list[dict] = []
    gallery_audios: list[dict] = []
    gallery_docs: list[dict] = []
    gallery_links: list[dict] = []

    for idx, msg in enumerate(messages):
        if is_system_message(msg["content"]):
            continue
        clean_content, _ = strip_annotations(msg["content"])
        sender = msg["sender"]
        time_str = msg["dt"].strftime("%d/%m/%Y %H:%M") if msg.get("dt") else msg["date"]
        fname = get_attachment_filename(clean_content)
        msg_id = f"msg-{idx}"

        if fname:
            filepath = f"{rel_media}/{fname}".replace("//", "/")
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                thumb_disk_path = os.path.join(media_dir, ".thumbs", fname)
                thumb_filepath = f"{rel_media}/.thumbs/{fname}".replace("//", "/") if os.path.isfile(thumb_disk_path) else filepath
                gallery_photos.append({"src": filepath, "thumb": thumb_filepath, "sender": sender, "time": time_str, "msgId": msg_id})
            elif fname.lower().endswith(".webp"):
                # webp are stickers – include in photos tab but mark as sticker
                gallery_photos.append({"src": filepath, "sender": sender, "time": time_str, "sticker": True, "msgId": msg_id})
            elif fname.lower().endswith((".mp4", ".mov", ".3gp")):
                gallery_photos.append({"src": filepath, "sender": sender, "time": time_str, "video": True, "msgId": msg_id})
            elif fname.lower().endswith((".opus", ".mp3", ".ogg", ".m4a", ".aac")):
                gallery_audios.append({"src": filepath, "sender": sender, "time": time_str, "msgId": msg_id})
            elif fname.lower().endswith(".pdf"):
                gallery_docs.append({"href": filepath, "label": fname, "sender": sender, "time": time_str, "msgId": msg_id})
            else:
                gallery_docs.append({"href": filepath, "label": fname, "sender": sender, "time": time_str, "msgId": msg_id})
        else:
            # Extract URLs from plain-text messages
            found_urls = URL_PATTERN.findall(clean_content)
            for url in found_urls:
                gallery_links.append({"href": url, "label": url, "sender": sender, "time": time_str, "msgId": msg_id})

    return {
        "photos": gallery_photos,
        "audios": gallery_audios,
        "docs": gallery_docs,
        "links": gallery_links,
    }


def render_grouped_messages(
    messages: list[dict],
    media_dir: str,
    color_map: dict[str, str],
    output_dir: str = "",
    me_user: str | None = None,
) -> tuple[str, list[str], tuple[str, str]]:
    """Render messages grouped by sender into HTML with date separators and system notifications.

    Returns:
        (html_string, attendees_list, (start_date_str, end_date_str))
    """
    if not messages:
        return "", [], ("", "")

    grouped_html: list[str] = []
    attendees = list(dict.fromkeys(msg["sender"] for msg in messages))
    start_date = messages[0]["date"]
    end_date = messages[-1]["date"]
    last_day: str | None = None
    in_day_group = False
    i = 0

    while i < len(messages):
        msg = messages[i]
        current_sender = msg["sender"]
        sender_color = color_map.get(current_sender, "#128C7E")
        initials = "".join(w[0].upper() for w in current_sender.split()[:2])
        msg_dt = msg.get("dt")

        # ---- Date separator & Day Group ----
        if msg_dt:
            day_key = msg_dt.strftime("%Y-%m-%d")
            if day_key != last_day:
                last_day = day_key
                if in_day_group:
                    grouped_html.append("</div>")
                in_day_group = True
                grouped_html.append(
                    f'<div class="day-group" data-date="{day_key}" data-month="{day_key[:7]}">'
                )
                grouped_html.append(
                    f'<div class="date-separator" data-date="{day_key}" data-month="{day_key[:7]}">'
                    f'<span>{format_day_label(msg_dt)}</span>'
                    f'</div>'
                )

        # ---- System message ----
        if is_system_message(msg["content"]):
            icon = get_system_icon(msg["content"])
            clean = msg["content"].lstrip("\u200e").strip()
            grouped_html.append(
                f'<div class="system-message">'
                f'<span>{icon} {html.escape(clean)}</span>'
                f'</div>'
            )
            i += 1
            continue

        # ---- Regular message group (consecutive messages from same sender) ----
        group_texts: list[str] = []
        group_has_media = False
        group_media_types: set[str] = set()
        is_me = bool(me_user and current_sender == me_user)

        while i < len(messages) and messages[i]["sender"] == current_sender:
            cur = messages[i]

            # Stop group on day change
            if cur.get("dt"):
                dk = cur["dt"].strftime("%Y-%m-%d")
                if dk != last_day and group_texts:
                    break

            # Stop group on system message
            if is_system_message(cur["content"]):
                break

            clean_content, was_edited = strip_annotations(cur["content"])
            filename = get_attachment_filename(clean_content)
            has_file = filename is not None
            sub_media_type = ""
            if has_file:
                group_has_media = True
                fn_lower = filename.lower()
                if fn_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    sub_media_type = "photo"
                elif fn_lower.endswith((".mp4", ".mov", ".3gp")):
                    sub_media_type = "video"
                elif fn_lower.endswith((".opus", ".mp3", ".ogg", ".m4a", ".aac")):
                    sub_media_type = "audio"
                elif fn_lower.endswith(".pdf"):
                    sub_media_type = "doc"
                else:
                    sub_media_type = "doc"
                content_html = render_attachment(filename, media_dir, output_dir=output_dir)
            else:
                if URL_PATTERN.search(clean_content):
                    sub_media_type = "link"
                content_html = format_message(clean_content).replace("\n", "<br>")

            if sub_media_type:
                group_media_types.add(sub_media_type)

            time_display = cur["dt"].strftime("%H:%M") if cur.get("dt") else cur["date"]
            edited_badge = ' <span class="edited-badge">modifié</span>' if was_edited else ""
            status_check = ' <span class="msg-status" title="Lu">✓✓</span>' if is_me else ""
            type_class = f" media-type-{sub_media_type}" if sub_media_type else ""
            sub_class = f"with-file{type_class}" if has_file else (type_class.strip())
            type_attr = f' data-media-type="{sub_media_type}"' if sub_media_type else ""

            group_texts.append(
                f'<div class="sub-message {sub_class}" id="msg-{i}"{type_attr}>'
                f'<div class="text">{content_html}</div>'
                f'<div class="time">{time_display}{edited_badge}{status_check}</div>'
                f'</div>'
            )
            i += 1

        if group_texts:
            month_val = last_day[:7] if last_day else ""
            types_str = " ".join(sorted(group_media_types))
            grouped_html.append(
                build_bubble(
                    current_sender,
                    sender_color,
                    initials,
                    group_texts,
                    is_me=is_me,
                    has_media=group_has_media,
                    month=month_val,
                    media_types=types_str,
                )
            )

    if in_day_group:
        grouped_html.append("</div>")

    return "\n".join(grouped_html), attendees, (start_date, end_date)


def build_html(
    messages: list[dict],
    media_dir: str,
    output_path: str = "",
    me_user: str | None = None,
    minify: bool = True,
) -> str:
    """Build the full self-contained HTML page from parsed messages."""
    if not messages:
        return "<!DOCTYPE html><html><body><p>Aucun message.</p></body></html>"

    attendee_list = list(dict.fromkeys(msg["sender"] for msg in messages))
    color_map = {
        name: AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        for idx, name in enumerate(attendee_list)
    }

    resolved_me = resolve_me_user(me_user, attendee_list) if me_user else None

    output_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else ""
    grouped_html, attendees, (start_date, end_date) = render_grouped_messages(
        messages, media_dir, color_map, output_dir=output_dir, me_user=resolved_me
    )

    # Collect gallery data (photos, audios, docs, links)
    gallery_data = _collect_gallery_data(messages, media_dir, output_dir=output_dir)
    gallery_data_json = json.dumps(gallery_data, ensure_ascii=False)
    total_media_count = (
        len(gallery_data["photos"])
        + len(gallery_data["audios"])
        + len(gallery_data["docs"])
        + len(gallery_data["links"])
    )

    stats = compute_stats(messages)
    stats_html = render_stats_html(stats, color_map)

    is_group = len(attendees) > 2
    chat_label = "Conversation de groupe WhatsApp" if is_group else "Conversation WhatsApp"
    title = f"{chat_label} - {' & '.join(attendees)}"

    me_options = ['<option value="">-- Aucun (Tous à gauche) --</option>']
    for a in attendees:
        sel = ' selected="selected"' if (resolved_me and a == resolved_me) else ''
        me_options.append(f'<option value="{html.escape(a)}"{sel}>{html.escape(a)}</option>')
    me_options_html = "\n          ".join(me_options)

    legend_items = "".join(
        f'<span class="legend-item{" legend-active-me" if resolved_me == a else ""}" '
        f'data-sender="{html.escape(a)}" '
        f'onclick="setMeUser(\'{html.escape(a, quote=True)}\')" '
        f'title="Cliquer pour afficher en tant que \'Moi\'">'
        f'<span class="legend-dot" style="background:{color_map[a]};"></span>'
        f'{html.escape(a)}</span>'
        for a in attendees
    )

    attendees_header = ' &amp; '.join(html.escape(a) for a in attendees)

    participant_css = "\n".join(
        f'.message-row[data-sender="{html.escape(name, quote=True)}"] {{ --user-color: {color}; }}'
        for name, color in color_map.items()
    )
    style_content = load_template_file("style.css") + "\n\n/* Dynamic Participant Color Variables */\n" + participant_css
    script_content = load_template_file("app.js")
    base_html = load_template_file("base.html")

    replacements = {
        "{{ title }}": html.escape(title),
        "{{ style }}": style_content,
        "{{ initial_me }}": html.escape(resolved_me or ""),
        "{{ chat_label }}": html.escape(chat_label),
        "{{ attendees_header }}": attendees_header,
        "{{ start_date }}": html.escape(start_date),
        "{{ end_date }}": html.escape(end_date),
        "{{ me_options_html }}": me_options_html,
        "{{ legend_items }}": legend_items,
        "{{ grouped_html }}": grouped_html,
        "{{ stats_html }}": stats_html,
        "{{ script }}": script_content,
        "{{ gallery_data }}": gallery_data_json,
        "{{ media_count }}": str(total_media_count),
    }

    result = base_html
    for placeholder, val in replacements.items():
        result = result.replace(placeholder, val)

    return minify_html(result) if minify else result


def minify_html(html_str: str) -> str:
    """Minify HTML by stripping empty lines, leading/trailing whitespace, and HTML comments,
    while preserving <pre>, <code>, <script>, and <style> contents.
    """
    if not html_str:
        return ""

    preserved: list[str] = []

    def preserve_block(match: re.Match) -> str:
        idx = len(preserved)
        preserved.append(match.group(0))
        return f"__PRESERVED_BLOCK_{idx}__"

    pattern = re.compile(r"<(pre|code|script|style)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
    protected = pattern.sub(preserve_block, html_str)

    # Remove non-conditional HTML comments
    protected = re.sub(r"<!--(?!\[if).*?-->", "", protected, flags=re.DOTALL)

    # Strip line whitespace and drop blank lines
    lines = [line.strip() for line in protected.splitlines()]
    minified = "\n".join(line for line in lines if line)

    # Restore preserved blocks
    for idx, block in enumerate(preserved):
        minified = minified.replace(f"__PRESERVED_BLOCK_{idx}__", block, 1)

    return minified.strip()
