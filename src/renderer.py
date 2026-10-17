"""HTML generation and message rendering for WhatsApp conversations."""

import html
import os
from src.constants import AVATAR_COLORS
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
    parts = filename.split("-")
    file_type = parts[1].upper() if len(parts) >= 2 else ""

    if file_type == "STICKER":
        return f'<img src="{filepath}" class="sticker-img" alt="Sticker" loading="lazy" decoding="async">'
    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
        return f'<img src="{filepath}" class="media-img" alt="Image" loading="lazy" decoding="async">'
    if filename.lower().endswith(".webp"):
        return f'<img src="{filepath}" class="sticker-img" alt="Sticker" loading="lazy" decoding="async">'
    if filename.lower().endswith((".mp4", ".mov", ".3gp")):
        return (
            f'<video controls preload="none" class="media-video">'
            f'<source src="{filepath}">Vidéo non supportée.</video>'
        )
    if filename.lower().endswith((".opus", ".mp3", ".ogg", ".m4a", ".aac")):
        return (
            f'<div class="audio-container">'
            f'<audio controls preload="none" src="{filepath}"></audio>'
            f'<button type="button" class="audio-speed-btn" onclick="toggleAudioSpeed(this)" title="Changer la vitesse (1x, 1.5x, 2x)">1x</button>'
            f'</div>'
        )
    if filename.lower().endswith(".pdf"):
        return f'<a href="{filepath}" target="_blank">📄 {html.escape(filename)}</a>'
    return f'<a href="{filepath}">📎 {html.escape(filename)}</a>'


def build_bubble(
    sender: str,
    color: str,
    initials: str,
    group_texts: list[str],
    is_me: bool = False,
) -> str:
    """Build the HTML for a single message bubble (one sender, one or more sub-messages)."""
    avatar = (
        f'<div class="avatar" style="background:{color};" title="{html.escape(sender)}">'
        f'{html.escape(initials)}</div>'
    )
    sender_label = f'<div class="sender" style="color:{color};">{html.escape(sender)}</div>'
    me_class = " is-me" if is_me else ""
    return (
        f'<div class="message-row{me_class}" data-sender="{html.escape(sender)}">'
        f'{avatar}'
        f'<div class="message">{sender_label}{"".join(group_texts)}</div>'
        f'</div>'
    )


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
    i = 0

    while i < len(messages):
        msg = messages[i]
        current_sender = msg["sender"]
        sender_color = color_map.get(current_sender, "#128C7E")
        initials = "".join(w[0].upper() for w in current_sender.split()[:2])
        msg_dt = msg.get("dt")

        # ---- Date separator ----
        if msg_dt:
            day_key = msg_dt.strftime("%Y-%m-%d")
            if day_key != last_day:
                last_day = day_key
                grouped_html.append(
                    f'<div class="date-separator">'
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

            if has_file:
                content_html = render_attachment(filename, media_dir, output_dir=output_dir)
            else:
                content_html = format_message(clean_content).replace("\n", "<br>")

            time_display = cur["dt"].strftime("%H:%M") if cur.get("dt") else cur["date"]
            edited_badge = ' <span class="edited-badge">modifié</span>' if was_edited else ""
            sub_class = "with-file" if has_file else ""

            group_texts.append(
                f'<div class="sub-message {sub_class}">'
                f'<div class="text">{content_html}</div>'
                f'<div class="time">{time_display}{edited_badge}</div>'
                f'</div>'
            )
            i += 1

        if group_texts:
            is_me = bool(me_user and current_sender == me_user)
            grouped_html.append(
                build_bubble(current_sender, sender_color, initials, group_texts, is_me=is_me)
            )

    return "\n".join(grouped_html), attendees, (start_date, end_date)


def build_html(
    messages: list[dict],
    media_dir: str,
    output_path: str = "",
    me_user: str | None = None,
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

    style_content = load_template_file("style.css")
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
    }

    result = base_html
    for placeholder, val in replacements.items():
        result = result.replace(placeholder, val)

    return result
