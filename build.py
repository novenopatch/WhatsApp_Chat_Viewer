import re
import os
import html
import argparse
from datetime import datetime
from collections import Counter

# ---------------------------------------------------------------------------
# Regex patterns & constants
# ---------------------------------------------------------------------------

message_pattern = re.compile(
    r"^\u200e?\[(\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}:\d{2})\] ([^:]+): (.*)$"
)

ATTACHMENT_KEYWORDS = ["pièce jointe :", "file attached:", "attached:"]

DATE_FORMATS = [
    "%d/%m/%y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
    "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
]

AVATAR_COLORS = [
    "#25D366", "#128C7E", "#075E54", "#34B7F1",
    "#E84393", "#FF6B6B", "#FFB347", "#A29BFE",
]

FRENCH_MONTHS = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

SYSTEM_MESSAGE_PATTERN = re.compile(
    r"(?:"
    r"Appel (?:vocal|vidéo|de groupe)"
    r"|chiffr[ée]s? de bout en bout"
    r"|audio omis"
    r"|Vous avez supprimé ce message"
    r"|Ce message a été supprimé"
    r"|en silencieux"
    r"|Répondu sur un autre appareil"
    r"|Appuyez pour rappeler"
    r")",
    re.IGNORECASE,
)

EDIT_ANNOTATION_PATTERN   = re.compile(r"\s*\u200e?<Ce message a été modifié>\s*$")
DELETE_ANNOTATION_PATTERN = re.compile(r"\s*\u200e?<Ce message a été supprimé>\s*$")
URL_PATTERN               = re.compile(r"(https?://[^\s<>\"']+)")

# WhatsApp markdown (applied on HTML-escaped text; *, _, ~, ` not HTML-special)
_WA_CODE_BLOCK = re.compile(r"```([\s\S]+?)```")
_WA_MONO       = re.compile(r"`([^`\n]+)`")
_WA_BOLD       = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
_WA_ITALIC     = re.compile(r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)")
_WA_STRIKE     = re.compile(r"(?<!~)~(?!\s)(.+?)(?<!\s)~(?!~)")

SYSTEM_ICONS = {
    "appel vocal": "📞", "appel vidéo": "📹", "appel de groupe": "👥",
    "chiffr": "🔒",      "audio omis": "🎤",  "supprimé": "🗑️",
    "silencieux": "🔕",  "rappeler": "📵",    "répondu": "📱",
}

MEDIA_TYPE_MAP = {
    "AUDIO":    "🎤 Audio",
    "PHOTO":    "📷 Photo",
    "VIDEO":    "🎬 Vidéo",
    "STICKER":  "🎭 Sticker",
    "GIF":      "🎞️ GIF",
    "DOCUMENT": "📄 Document",
}

# ---------------------------------------------------------------------------
# Module-level HTML/JS snippets
# (kept outside the build_html f-string so braces/backslashes are literal)
# ---------------------------------------------------------------------------

_LIGHTBOX_HTML = """
  <div id="lightbox">
    <button id="lb-close" title="Fermer (Échap)">&#x2715;</button>
    <button id="lb-prev"  title="Précédent (←)">&#8249;</button>
    <img    id="lightbox-img" src="" alt="Image agrandie">
    <button id="lb-next"  title="Suivant (→)">&#8250;</button>
  </div>
"""

_SCROLL_HTML = """
  <div id="scroll-btns">
    <button onclick="window.scrollTo({top:0,behavior:'smooth'})"                      title="Haut de page">&#8679;</button>
    <button onclick="window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})" title="Bas de page">&#8681;</button>
  </div>
"""

# Raw string → backslashes are literal → no Python escape issues
_JS = r"""
  // =========================================================================
  // Search with keyboard navigation
  // =========================================================================
  const chatContainer = document.getElementById('chat-container');
  const searchInput   = document.getElementById('search-input');
  const searchCount   = document.getElementById('search-count');
  const btnPrev       = document.getElementById('search-prev');
  const btnNext       = document.getElementById('search-next');

  const originalHTML  = chatContainer.innerHTML;
  let searchMatches   = [];
  let currentMatchIdx = -1;

  function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function clearSearch() {
    chatContainer.innerHTML = originalHTML;
    searchMatches   = [];
    currentMatchIdx = -1;
    searchCount.textContent = '';
    btnPrev.disabled = true;
    btnNext.disabled = true;
    attachImageListeners();
  }

  function runSearch(query) {
    chatContainer.innerHTML = originalHTML;
    searchMatches   = [];
    currentMatchIdx = -1;

    const q = query.trim();
    if (!q) { clearSearch(); return; }

    const regex = new RegExp('(' + escapeRegex(q) + ')', 'gi');

    chatContainer.querySelectorAll('.sub-message .text').forEach(el => {
      el.innerHTML = el.innerHTML.replace(regex, '<mark>$1</mark>');
    });

    chatContainer.querySelectorAll('.message-row').forEach(row => {
      row.classList.toggle('search-hidden', !row.querySelector('mark'));
    });

    chatContainer.querySelectorAll('.date-separator').forEach(sep => {
      let next = sep.nextElementSibling;
      let vis  = false;
      while (next && !next.classList.contains('date-separator')) {
        if (!next.classList.contains('search-hidden')) { vis = true; break; }
        next = next.nextElementSibling;
      }
      sep.classList.toggle('search-hidden', !vis);
    });

    searchMatches    = Array.from(chatContainer.querySelectorAll('mark'));
    btnPrev.disabled = searchMatches.length === 0;
    btnNext.disabled = searchMatches.length === 0;

    if (searchMatches.length > 0) goToMatch(0);
    else searchCount.textContent = 'Aucun résultat';

    attachImageListeners();
  }

  function goToMatch(idx) {
    if (!searchMatches.length) return;
    searchMatches.forEach(m => m.classList.remove('match-active'));
    currentMatchIdx = ((idx % searchMatches.length) + searchMatches.length) % searchMatches.length;
    const active = searchMatches[currentMatchIdx];
    active.classList.add('match-active');
    active.scrollIntoView({ behavior: 'smooth', block: 'center' });
    searchCount.textContent = (currentMatchIdx + 1) + ' / ' + searchMatches.length;
  }

  searchInput.addEventListener('input',   e => runSearch(e.target.value));
  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter')  { e.preventDefault(); goToMatch(e.shiftKey ? currentMatchIdx - 1 : currentMatchIdx + 1); }
    if (e.key === 'Escape') { searchInput.value = ''; clearSearch(); }
  });
  btnPrev.addEventListener('click', () => goToMatch(currentMatchIdx - 1));
  btnNext.addEventListener('click', () => goToMatch(currentMatchIdx + 1));

  // =========================================================================
  // Lightbox
  // =========================================================================
  const lightbox    = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightbox-img');
  let lbImages = [];
  let lbIdx    = 0;

  function attachImageListeners() {
    document.querySelectorAll('.media-img').forEach(img => {
      img.onclick = () => openLightbox(img);
    });
  }

  function openLightbox(img) {
    lbImages = Array.from(document.querySelectorAll('.media-img'));
    lbIdx    = lbImages.indexOf(img);
    lightboxImg.src = img.src;
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
  }

  function lbMove(delta) {
    if (!lbImages.length) return;
    lbIdx = ((lbIdx + delta + lbImages.length) % lbImages.length);
    lightboxImg.src = lbImages[lbIdx].src;
  }

  document.getElementById('lb-close').addEventListener('click', closeLightbox);
  document.getElementById('lb-prev').addEventListener('click',  () => lbMove(-1));
  document.getElementById('lb-next').addEventListener('click',  () => lbMove(+1));
  lightbox.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });

  document.addEventListener('keydown', e => {
    if (!lightbox.classList.contains('active')) return;
    if (e.key === 'Escape')     closeLightbox();
    if (e.key === 'ArrowLeft')  lbMove(-1);
    if (e.key === 'ArrowRight') lbMove(+1);
  });

  attachImageListeners();
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(date_str: str) -> datetime | None:
    """Try to parse a WhatsApp date string into a datetime object."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def format_day_label(dt: datetime) -> str:
    """Return a human-readable French day label, e.g. 'Lundi 3 mars 2024'."""
    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return f"{day_names[dt.weekday()]} {dt.day} {FRENCH_MONTHS[dt.month]} {dt.year}"


def get_attachment_filename(raw_content: str) -> str | None:
    """Extract the filename from an attachment line, return None if not an attachment."""
    for kw in ATTACHMENT_KEYWORDS:
        if kw in raw_content:
            return raw_content.split(kw)[-1].strip(" \u202a<>")
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
    """
    Convert raw WhatsApp message text to HTML:
      1. Split out URLs first (so markdown doesn't corrupt them)
      2. HTML-escape text segments
      3. Apply WhatsApp markdown (*bold*, _italic_, ~strike~, `mono`, ```block```)
      4. Wrap URLs in <a> tags
    """
    parts = URL_PATTERN.split(text)   # odd indices = URLs
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:                # URL
            esc = html.escape(part)
            result.append(
                f'<a href="{esc}" target="_blank" rel="noopener noreferrer">{esc}</a>'
            )
        else:
            esc = html.escape(part)
            # Apply WA markdown (order matters: code blocks first)
            esc = _WA_CODE_BLOCK.sub(r"<pre><code>\1</code></pre>", esc)
            esc = _WA_MONO.sub(r"<code>\1</code>", esc)
            esc = _WA_BOLD.sub(r"<strong>\1</strong>", esc)
            esc = _WA_ITALIC.sub(r"<em>\1</em>", esc)
            esc = _WA_STRIKE.sub(r"<del>\1</del>", esc)
            result.append(esc)
    return "".join(result)


def strip_annotations(content: str) -> tuple[str, bool]:
    """
    Remove inline edit/delete markers from message content.
    Returns (cleaned_content, was_edited).
    """
    was_edited = bool(EDIT_ANNOTATION_PATTERN.search(content))
    content = EDIT_ANNOTATION_PATTERN.sub("", content)
    content = DELETE_ANNOTATION_PATTERN.sub("", content)
    return content.strip(), was_edited


def render_attachment(filename: str, media_dir: str, output_dir: str = "") -> str:
    """Return the HTML snippet for a given attachment filename."""
    if output_dir:
        rel_media_dir = os.path.relpath(media_dir, output_dir).replace("\\", "/")
    else:
        rel_media_dir = media_dir.replace("\\", "/")
    
    filepath = f"{rel_media_dir}/{filename}".replace("//", "/")
    parts     = filename.split("-")
    file_type = parts[1].upper() if len(parts) >= 2 else ""

    if file_type == "STICKER":
        return f'<img src="{filepath}" class="sticker-img" alt="Sticker" loading="lazy">'
    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
        return f'<img src="{filepath}" class="media-img" alt="Image" loading="lazy">'
    if filename.lower().endswith(".webp"):
        return f'<img src="{filepath}" class="sticker-img" alt="Sticker" loading="lazy">'
    if filename.lower().endswith((".mp4", ".mov", ".3gp")):
        return (
            f'<video controls preload="none" class="media-video">'
            f'<source src="{filepath}">Vidéo non supportée.</video>'
        )
    if filename.lower().endswith((".opus", ".mp3", ".ogg", ".m4a", ".aac")):
        return f'<audio controls preload="none" src="{filepath}"></audio>'
    if filename.lower().endswith(".pdf"):
        return f'<a href="{filepath}" target="_blank">📄 {html.escape(filename)}</a>'
    return f'<a href="{filepath}">📎 {html.escape(filename)}</a>'


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_chat(file_path: str) -> list[dict]:
    """Parse a WhatsApp exported .txt file into a list of message dicts."""
    messages = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            match = message_pattern.match(line)
            if match:
                date, sender, content = match.groups()
                messages.append({
                    "date":   date,
                    "sender": sender.strip(),
                    "content": content,
                    "dt":     parse_date(date),
                })
            elif messages:
                messages[-1]["content"] += "\n" + line
    return messages


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def compute_stats(messages: list[dict]) -> dict:
    """Compute chat statistics (messages per sender, hourly activity, media types, …)."""
    real = [m for m in messages if not is_system_message(m["content"])]

    sender_counts = Counter(m["sender"] for m in real)
    hour_counts   = Counter()
    day_counts    = Counter()
    media_counts  = Counter()

    for m in real:
        if m["dt"]:
            hour_counts[m["dt"].hour] += 1
            day_counts[m["dt"].strftime("%Y-%m-%d")] += 1
        fname = get_attachment_filename(m["content"])
        if fname:
            media_counts[get_media_type_label(fname)] += 1

    most_active = day_counts.most_common(1)[0] if day_counts else ("", 0)
    return {
        "total":          len(messages),
        "real_total":     len(real),
        "sender_counts":  sender_counts,
        "hour_counts":    hour_counts,
        "day_counts":     day_counts,
        "most_active":    most_active,
        "media_counts":   media_counts,
    }


def render_stats_html(stats: dict, color_map: dict[str, str]) -> str:
    """Build the collapsible stats <details> section."""
    real_total = stats["real_total"]

    # ---- Sender bars ----
    sender_bars = ""
    for sender, count in stats["sender_counts"].most_common():
        pct   = count / real_total * 100 if real_total else 0
        color = color_map.get(sender, "#128C7E")
        sender_bars += (
            f'<div class="sbar-row">'
            f'<span class="sbar-name" style="color:{color}">{html.escape(sender)}</span>'
            f'<div class="sbar-track">'
            f'<div class="sbar-fill" style="width:{pct:.1f}%;background:{color}"></div>'
            f'</div>'
            f'<span class="sbar-count">{count:,} <small>({pct:.0f}%)</small></span>'
            f'</div>'
        )

    # ---- Hourly chart (24 bars) ----
    max_hour = max(stats["hour_counts"].values(), default=1)
    hour_bars = ""
    for h in range(24):
        cnt = stats["hour_counts"].get(h, 0)
        pct = cnt / max_hour * 100 if max_hour else 0
        lbl = f"{h}h" if h % 4 == 0 else ""
        hour_bars += (
            f'<div class="hcol" title="{h}h : {cnt:,} messages">'
            f'<div class="hbar" style="height:{pct:.0f}%"></div>'
            f'<span class="hlbl">{lbl}</span>'
            f'</div>'
        )

    # ---- Media breakdown ----
    media_rows = "".join(
        f'<div class="mrow"><span>{lbl}</span><strong>{cnt:,}</strong></div>'
        for lbl, cnt in stats["media_counts"].most_common()
    ) or "<em style='color:#999'>Aucun média</em>"

    # ---- General info ----
    mad_str, mad_cnt = stats["most_active"]
    if mad_str:
        try:
            mad_label = format_day_label(datetime.strptime(mad_str, "%Y-%m-%d"))
        except ValueError:
            mad_label = mad_str
    else:
        mad_label, mad_cnt = "N/A", 0

    total_days = len(stats["day_counts"])
    avg_day    = real_total / total_days if total_days else 0
    total_media = sum(stats["media_counts"].values())

    gen_rows = (
        f'<div class="grow"><span>Total messages</span><strong>{real_total:,}</strong></div>'
        f'<div class="grow"><span>Durée</span><strong>{total_days} jours</strong></div>'
        f'<div class="grow"><span>Moy. / jour</span><strong>{avg_day:.0f} msgs</strong></div>'
        f'<div class="grow"><span>Médias échangés</span><strong>{total_media:,}</strong></div>'
        f'<div class="grow"><span>Jour le + actif</span><strong>{html.escape(mad_label)}</strong></div>'
        f'<div class="grow"><span>Record du jour</span><strong>{mad_cnt:,} msgs</strong></div>'
    )

    return f"""
<details class="stats-section">
  <summary>📊 Statistiques de la conversation</summary>
  <div class="stats-grid">
    <div class="stats-box">
      <h3>💬 Messages par personne</h3>
      <div class="sender-bars">{sender_bars}</div>
    </div>
    <div class="stats-box">
      <h3>⏰ Activité par heure</h3>
      <div class="hour-chart">{hour_bars}</div>
    </div>
    <div class="stats-box">
      <h3>📎 Médias échangés</h3>
      <div class="media-rows">{media_rows}</div>
    </div>
    <div class="stats-box">
      <h3>📅 Infos générales</h3>
      <div class="gen-rows">{gen_rows}</div>
    </div>
  </div>
</details>
"""


# ---------------------------------------------------------------------------
# HTML Renderer
# ---------------------------------------------------------------------------

def render_grouped_messages(
    messages: list[dict],
    media_dir: str,
    color_map: dict[str, str],
    output_dir: str = "",
) -> tuple[str, list[str], tuple[str, str]]:
    """
    Render messages grouped by sender into HTML with date separators
    and distinct styling for system notifications.

    Returns:
        (html_string, attendees_list, (start_date_str, end_date_str))
    """
    grouped_html: list[str] = []
    attendees  = list(dict.fromkeys(msg["sender"] for msg in messages))
    start_date = messages[0]["date"]
    end_date   = messages[-1]["date"]
    last_day: str | None = None
    i = 0

    while i < len(messages):
        msg            = messages[i]
        current_sender = msg["sender"]
        sender_color   = color_map.get(current_sender, "#128C7E")
        initials       = "".join(w[0].upper() for w in current_sender.split()[:2])
        msg_dt         = msg["dt"]

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
            icon  = get_system_icon(msg["content"])
            clean = msg["content"].lstrip("\u200e").strip()
            grouped_html.append(
                f'<div class="system-message">'
                f'<span>{icon} {html.escape(clean)}</span>'
                f'</div>'
            )
            i += 1
            continue

        # ---- Regular message group (same sender, consecutive) ----
        group_texts: list[str] = []

        while i < len(messages) and messages[i]["sender"] == current_sender:
            cur = messages[i]

            # Stop group on day change (separator inserted next iteration)
            if cur["dt"]:
                dk = cur["dt"].strftime("%Y-%m-%d")
                if dk != last_day and group_texts:
                    break

            # Stop group on system messages
            if is_system_message(cur["content"]):
                break

            clean_content, was_edited = strip_annotations(cur["content"])
            filename = get_attachment_filename(clean_content)
            has_file = filename is not None

            if has_file:
                content_html = render_attachment(filename, media_dir, output_dir=output_dir)
            else:
                content_html = format_message(clean_content).replace("\n", "<br>")

            time_display = cur["dt"].strftime("%H:%M") if cur["dt"] else cur["date"]
            edited_badge = ' <span class="edited-badge">modifié</span>' if was_edited else ""
            sub_class    = "with-file" if has_file else ""

            group_texts.append(
                f'<div class="sub-message {sub_class}">'
                f'<div class="text">{content_html}</div>'
                f'<div class="time">{time_display}{edited_badge}</div>'
                f'</div>'
            )
            i += 1

        if group_texts:
            grouped_html.append(
                _build_bubble(current_sender, sender_color, initials, group_texts)
            )

    return "\n".join(grouped_html), attendees, (start_date, end_date)


def _build_bubble(
    sender: str,
    color: str,
    initials: str,
    group_texts: list[str],
) -> str:
    """Build the HTML for a single message bubble (one sender, one or more sub-messages)."""
    avatar = (
        f'<div class="avatar" style="background:{color};" title="{html.escape(sender)}">'
        f'{html.escape(initials)}</div>'
    )
    sender_label = f'<div class="sender" style="color:{color};">{html.escape(sender)}</div>'
    return (
        f'<div class="message-row">'
        f'{avatar}'
        f'<div class="message">{sender_label}{"".join(group_texts)}</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# HTML Builder
# ---------------------------------------------------------------------------

def build_html(messages: list[dict], media_dir: str, output_path: str = "") -> str:
    """Build the full HTML page from parsed messages."""
    attendee_list = list(dict.fromkeys(msg["sender"] for msg in messages))
    color_map = {
        name: AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        for idx, name in enumerate(attendee_list)
    }

    output_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else ""
    grouped_html, attendees, (start_date, end_date) = render_grouped_messages(
        messages, media_dir, color_map, output_dir=output_dir
    )

    stats     = compute_stats(messages)
    stats_html = render_stats_html(stats, color_map)

    is_group     = len(attendees) > 2
    chat_label   = "Conversation de groupe" if is_group else "Conversation"
    legend_items = "".join(
        f'<span class="legend-item">'
        f'<span class="legend-dot" style="background:{color_map[a]};"></span>'
        f'{html.escape(a)}</span>'
        for a in attendees
    )

    # _LIGHTBOX_HTML, _SCROLL_HTML, _JS are module-level strings → no f-string escaping needed
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(chat_label)} WhatsApp</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}

    body {{
        font-family: Arial, sans-serif;
        background: #ece5dd;
        margin: 0; padding: 0;
        display: flex; flex-direction: column; min-height: 100vh;
    }}

    /* ---- Top bar ---- */
    .top-bar {{
        position: sticky; top: 0; z-index: 100;
        background: #075E54; color: #fff;
        padding: 8px 16px;
        display: flex; align-items: center; gap: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,.3);
    }}
    .top-bar h1 {{ font-size: 15px; margin: 0; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .search-wrapper {{ position: relative; display: flex; align-items: center; gap: 4px; }}
    #search-input {{
        padding: 5px 28px 5px 10px; border-radius: 20px; border: none;
        font-size: 14px; width: 200px; outline: none;
    }}
    .search-icon {{ position: absolute; right: 78px; font-size: 13px; color: #555; pointer-events: none; }}
    .search-nav button {{
        background: rgba(255,255,255,.18); border: none; color: #fff;
        border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 14px;
    }}
    .search-nav button:disabled {{ opacity: .35; cursor: default; }}
    .search-nav button:not(:disabled):hover {{ background: rgba(255,255,255,.32); }}
    #search-count {{ font-size: 12px; white-space: nowrap; min-width: 64px; text-align: right; }}

    /* ---- Conversation header ---- */
    .conversation-header {{
        text-align: center; margin: 16px auto 8px;
        padding: 12px 20px; background: #fff;
        border-radius: 12px; max-width: 800px; width: calc(100% - 32px);
        box-shadow: 0 1px 3px rgba(0,0,0,.1);
    }}
    .conversation-header h2 {{ margin: 0 0 4px; font-size: 17px; color: #111; }}
    .conversation-header p  {{ margin: 0; font-size: 13px; color: #777; }}
    .legend {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 10px; }}
    .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 13px; color: #333; }}
    .legend-dot  {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}

    /* ---- Chat container ---- */
    .chat-container {{ max-width: 800px; width: calc(100% - 32px); margin: 0 auto 12px; padding: 10px 0; }}

    /* ---- Date separator ---- */
    .date-separator {{ text-align: center; margin: 16px 0 8px; }}
    .date-separator span {{
        display: inline-block; background: #cfe9ba; color: #444;
        font-size: 12px; padding: 4px 12px; border-radius: 12px;
    }}

    /* ---- System message ---- */
    .system-message {{ text-align: center; margin: 6px 0; }}
    .system-message span {{
        display: inline-block; background: rgba(255,255,255,.75); color: #666;
        font-size: 12px; padding: 3px 12px; border-radius: 12px;
        border: 1px solid #d8d8d8; font-style: italic; max-width: 85%;
    }}

    /* ---- Message rows ---- */
    .message-row {{ display: flex; align-items: flex-end; gap: 8px; margin: 6px 0; }}

    /* ---- Avatar ---- */
    .avatar {{
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 13px; font-weight: bold; color: #fff; flex-shrink: 0;
    }}

    /* ---- Bubble ---- */
    .message {{
        padding: 8px 12px; border-radius: 10px; border-bottom-left-radius: 2px;
        max-width: 68%; word-break: break-word;
        background: #fff; border: 1px solid #e0e0e0;
    }}
    .sender {{ font-weight: bold; font-size: 13px; margin-bottom: 4px; }}

    /* ---- Sub-messages ---- */
    .sub-message {{ margin: 3px 0; }}
    .sub-message .text {{ font-size: 14px; line-height: 1.45; }}
    .sub-message .time {{ font-size: 11px; color: #888; text-align: right; margin-top: 2px; }}
    .edited-badge {{ font-size: 10px; color: #bbb; margin-left: 4px; font-style: italic; }}

    /* ---- WhatsApp markdown ---- */
    .text strong {{ font-weight: bold; }}
    .text em     {{ font-style: italic; }}
    .text del    {{ text-decoration: line-through; color: #999; }}
    .text code   {{ font-family: 'Courier New', monospace; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 13px; }}
    .text pre    {{ background: #f4f4f4; border-radius: 6px; padding: 8px 10px; overflow-x: auto; margin: 4px 0; }}
    .text pre code {{ background: none; padding: 0; }}

    /* ---- Links ---- */
    .text a {{ color: #128C7E; text-decoration: underline; word-break: break-all; }}
    .text a:hover {{ color: #075E54; }}

    /* ---- Media ---- */
    .media-img    {{ max-width: 220px; border-radius: 8px; display: block; cursor: zoom-in; }}
    .media-video  {{ max-width: 220px; border-radius: 8px; display: block; }}
    .sticker-img  {{ max-width: 110px; display: block; }}

    /* ---- Search highlight ---- */
    mark {{ background: #FFD700; color: #000; border-radius: 2px; padding: 0 1px; }}
    mark.match-active {{ background: #FF8C00; color: #fff; }}
    .search-hidden {{ display: none !important; }}

    /* ---- Lightbox ---- */
    #lightbox {{
        display: none; position: fixed; inset: 0;
        background: rgba(0,0,0,.88); z-index: 9000;
        align-items: center; justify-content: center; gap: 16px;
    }}
    #lightbox.active {{ display: flex; }}
    #lightbox-img {{ max-width: 90vw; max-height: 88vh; border-radius: 4px; object-fit: contain; }}
    #lb-close {{
        position: absolute; top: 14px; right: 18px;
        background: none; border: none; color: #fff; font-size: 26px;
        cursor: pointer; line-height: 1;
    }}
    #lb-prev, #lb-next {{
        background: rgba(255,255,255,.15); border: none; color: #fff;
        font-size: 40px; line-height: 1; padding: 8px 14px; border-radius: 6px;
        cursor: pointer; flex-shrink: 0;
    }}
    #lb-prev:hover, #lb-next:hover {{ background: rgba(255,255,255,.28); }}

    /* ---- Scroll buttons ---- */
    #scroll-btns {{
        position: fixed; bottom: 20px; right: 16px;
        display: flex; flex-direction: column; gap: 6px; z-index: 200;
    }}
    #scroll-btns button {{
        width: 36px; height: 36px; border-radius: 50%;
        background: #075E54; color: #fff; border: none;
        font-size: 18px; cursor: pointer; box-shadow: 0 2px 6px rgba(0,0,0,.3);
        display: flex; align-items: center; justify-content: center;
    }}
    #scroll-btns button:hover {{ background: #128C7E; }}

    /* ---- Stats section ---- */
    .stats-section {{
        max-width: 800px; width: calc(100% - 32px); margin: 0 auto 28px;
        background: #fff; border-radius: 12px; overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,.1);
    }}
    .stats-section summary {{
        padding: 12px 20px; cursor: pointer; font-weight: bold;
        font-size: 15px; color: #075E54; user-select: none;
        border-bottom: 1px solid #f0f0f0;
    }}
    .stats-section summary:hover {{ background: #f9f9f9; }}
    .stats-grid {{
        display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 1px; background: #f0f0f0;
    }}
    .stats-box {{ background: #fff; padding: 16px 20px; }}
    .stats-box h3 {{ margin: 0 0 12px; font-size: 14px; color: #333; }}

    /* Sender bars */
    .sbar-row {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 13px; }}
    .sbar-name {{ min-width: 100px; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: bold; }}
    .sbar-track {{ flex: 1; height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }}
    .sbar-fill  {{ height: 100%; border-radius: 4px; transition: width .4s; }}
    .sbar-count {{ font-size: 12px; color: #666; white-space: nowrap; }}
    .sbar-count small {{ color: #aaa; }}

    /* Hour chart */
    .hour-chart {{
        display: flex; align-items: flex-end; gap: 2px;
        height: 80px; border-bottom: 1px solid #eee; padding-bottom: 2px;
    }}
    .hcol {{ display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; justify-content: flex-end; }}
    .hbar {{ width: 100%; background: #25D366; border-radius: 2px 2px 0 0; min-height: 2px; }}
    .hlbl {{ font-size: 9px; color: #999; margin-top: 3px; }}

    /* Media & general rows */
    .mrow, .grow {{ display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; border-bottom: 1px solid #f5f5f5; }}
    .mrow:last-child, .grow:last-child {{ border-bottom: none; }}
    .grow span {{ color: #666; }}
  </style>
</head>
<body>

  <!-- Sticky top bar -->
  <div class="top-bar">
    <h1>💬 {html.escape(chat_label)} WhatsApp</h1>
    <div class="search-wrapper">
      <input id="search-input" type="text" placeholder="Rechercher…" autocomplete="off">
      <span class="search-icon">🔍</span>
      <div class="search-nav">
        <button id="search-prev" disabled title="Résultat précédent (Shift+Entrée)">&#8679;</button>
        <button id="search-next" disabled title="Résultat suivant (Entrée)">&#8681;</button>
      </div>
    </div>
    <span id="search-count"></span>
  </div>

  <!-- Conversation header -->
  <div class="conversation-header">
    <h2>{' &amp; '.join(html.escape(a) for a in attendees)}</h2>
    <p>Du {html.escape(start_date)} au {html.escape(end_date)}</p>
    <div class="legend">{legend_items}</div>
  </div>

  <!-- Chat -->
  <div class="chat-container" id="chat-container">
    {grouped_html}
  </div>

  <!-- Stats -->
  {stats_html}

  <!-- Lightbox overlay -->
  {_LIGHTBOX_HTML}

  <!-- Scroll shortcuts -->
  {_SCROLL_HTML}

  <script>
  {_JS}
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Config loader  (4-tier: CLI args → .env → defaults → interactive prompt)
# ---------------------------------------------------------------------------

def _parse_dotenv(path: str) -> dict[str, str]:
    """
    Minimal .env parser — no external dependencies.
    Supports KEY=value, KEY="value", KEY='value', # comments.
    """
    env: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _find_chat_txt(directory: str) -> str | None:
    """Auto-discover the WhatsApp chat .txt inside *directory*."""
    for name in ("_chat.txt", "chat.txt"):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    for entry in sorted(os.listdir(directory)):
        if entry.endswith(".txt"):
            return os.path.join(directory, entry)
    return None


def _prompt(label: str, default: str = "") -> str:
    """Ask the user for a value with optional tab-completion."""
    try:
        import readline
        readline.set_completer_delims(" \t\n")
        readline.parse_and_bind("tab: complete")
    except ImportError:
        pass
    hint  = f"  [{default}]" if default else ""
    value = input(f"  {label}{hint} : ").strip()
    return value if value else default


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(
        prog="build.py",
        description="Convertit un export WhatsApp (.txt) en page HTML interactive.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python3 build.py --dir ~/exports/WhatsApp_Natacha/\n"
            "  python3 build.py --chat chat.txt --media media/ --output natacha.html\n"
            "\n"
            "Sans argument, le script lit .env puis les valeurs par défaut,\n"
            "et pose les questions manquantes de façon interactive."
        ),
    )
    p.add_argument("--chat",   "-c", metavar="FILE", help="Fichier de chat .txt")
    p.add_argument("--dir",    "-d", metavar="DIR",  help="Dossier d'export WhatsApp complet (auto-détection du .txt et media/)")
    p.add_argument("--media",  "-m", metavar="DIR",  help="Dossier des médias")
    p.add_argument("--output", "-o", metavar="FILE", help="Fichier HTML de sortie (défaut : output.html)")
    return p.parse_args()


def load_config() -> tuple[str, str, str]:
    """
    Resolve (chat_file, media_dir, output_file) with 4-tier priority:

    1. CLI arguments  (--chat / --dir / --media / --output)
    2. .env file      (CHAT_FILE / CHAT_DIR / MEDIA_DIR / OUTPUT_FILE)
    3. Defaults       (chat.txt + media/ in CWD, if they exist)
    4. Interactive    (prompts for anything still missing)
    """
    args = parse_args()

    chat_file:   str | None = None
    media_dir:   str | None = None
    output_file: str | None = None

    # ------------------------------------------------------------------
    # Tier 1 — CLI args
    # ------------------------------------------------------------------
    if args.dir:
        d = os.path.expanduser(args.dir)
        if os.path.isdir(d):
            found = _find_chat_txt(d)
            if found:
                chat_file = found
                candidate = os.path.join(d, "media")
                media_dir = candidate if os.path.isdir(candidate) else d
                print(f"📂 Dossier CLI détecté : {d}")
            else:
                print(f"⚠️  Aucun fichier .txt trouvé dans : {d}")
        else:
            print(f"⚠️  Dossier introuvable : {d}")

    if args.chat:
        chat_file = os.path.expanduser(args.chat)
    if args.media:
        media_dir = os.path.expanduser(args.media)
    if args.output:
        output_file = os.path.expanduser(args.output)

    # ------------------------------------------------------------------
    # Tier 2 — .env file
    # ------------------------------------------------------------------
    dotenv_path = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(dotenv_path):
        env = _parse_dotenv(dotenv_path)
        print("📄 Fichier .env détecté → lecture de la configuration…")

        if chat_file is None:
            chat_dir = env.get("CHAT_DIR", "").strip()
            if chat_dir and os.path.isdir(chat_dir):
                found = _find_chat_txt(chat_dir)
                if found:
                    chat_file = found
                    if media_dir is None:
                        candidate = os.path.join(chat_dir, "media")
                        media_dir = candidate if os.path.isdir(candidate) else chat_dir
            elif env.get("CHAT_FILE"):
                chat_file = env["CHAT_FILE"]

        if media_dir is None and env.get("MEDIA_DIR"):
            media_dir = env["MEDIA_DIR"]
        if output_file is None and env.get("OUTPUT_FILE"):
            output_file = env["OUTPUT_FILE"]

    # ------------------------------------------------------------------
    # Tier 3 — Defaults (CWD)
    # ------------------------------------------------------------------
    if chat_file is None:
        default_chat = os.path.join(os.getcwd(), "chat.txt")
        if os.path.isfile(default_chat):
            chat_file = default_chat
            print(f"📁 Fichier trouvé par défaut : {default_chat}")

    if media_dir is None:
        default_media = os.path.join(os.getcwd(), "media")
        if os.path.isdir(default_media):
            media_dir = default_media

    if output_file is None:
        output_file = os.path.join(os.getcwd(), "output.html")

    # ------------------------------------------------------------------
    # Tier 4 — Interactive prompt (anything still missing)
    # ------------------------------------------------------------------
    if chat_file is None:
        print("\n🔍 Aucune configuration automatique trouvée.")
        print("   Astuce : créez un .env (voir .env.example) ou utilisez --dir / --chat.\n")
        chat_file = _prompt(
            "Chemin du fichier de chat (.txt)",
            os.path.join(os.getcwd(), "chat.txt"),
        )

    if media_dir is None:
        guess = os.path.join(os.path.dirname(os.path.abspath(chat_file)), "media")
        print(f"\n📂 Dossier des médias introuvable automatiquement.")
        media_dir = _prompt("Dossier des médias (Entrée pour ignorer)", guess)

    return chat_file, media_dir, output_file


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    chat_file, media_dir, output_file = load_config()

    print(f"\n  chat    → {chat_file}")
    print(f"  médias  → {media_dir}")
    print(f"  sortie  → {output_file}\n")

    if not os.path.isfile(chat_file):
        print(f"❌ Fichier introuvable : {chat_file}")
        raise SystemExit(1)

    messages = parse_chat(chat_file)
    if not messages:
        print("⚠️  Aucun message trouvé. Vérifiez le fichier de chat.")
    else:
        html_output = build_html(messages, media_dir, output_path=output_file)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"✅ Fichier généré : {output_file}  ({len(messages):,} messages)")
