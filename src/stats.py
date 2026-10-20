"""Statistics calculation and HTML rendering for WhatsApp conversations."""

from __future__ import annotations

import html
from collections import Counter
from datetime import datetime
from src.i18n import get_translations, DEFAULT_LANGUAGE
from src.parser import is_system_message, get_attachment_filename, get_media_type_label, format_day_label


def compute_stats(messages: list[dict], lang: str = DEFAULT_LANGUAGE) -> dict:
    """Compute chat statistics (messages per sender, hourly activity, media types, etc.)."""
    real = [m for m in messages if not is_system_message(m["content"])]

    sender_counts = Counter(m["sender"] for m in real)
    hour_counts = Counter()
    day_counts = Counter()
    media_counts = Counter()

    for m in real:
        if m.get("dt"):
            hour_counts[m["dt"].hour] += 1
            day_counts[m["dt"].strftime("%Y-%m-%d")] += 1
        fname = get_attachment_filename(m["content"])
        if fname:
            media_counts[get_media_type_label(fname, lang=lang)] += 1

    most_active = day_counts.most_common(1)[0] if day_counts else ("", 0)
    return {
        "total": len(messages),
        "real_total": len(real),
        "sender_counts": sender_counts,
        "hour_counts": hour_counts,
        "day_counts": day_counts,
        "most_active": most_active,
        "media_counts": media_counts,
    }


def render_stats_html(stats: dict, color_map: dict[str, str], lang: str = DEFAULT_LANGUAGE) -> str:
    """Build the collapsible stats <details> HTML section."""
    t = get_translations(lang)
    real_total = stats["real_total"]

    # ---- Sender bars ----
    sender_bars = ""
    for sender, count in stats["sender_counts"].most_common():
        pct = count / real_total * 100 if real_total else 0
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
            f'<div class="hcol" title="{h}h : {cnt:,} {t["stat_msgs_hour"]}">'
            f'<div class="hbar" style="height:{pct:.0f}%"></div>'
            f'<span class="hlbl">{lbl}</span>'
            f'</div>'
        )

    # ---- Media breakdown ----
    media_rows = "".join(
        f'<div class="mrow"><span>{lbl}</span><strong>{cnt:,}</strong></div>'
        for lbl, cnt in stats["media_counts"].most_common()
    ) or f"<em style='color:var(--text-secondary)'>{t['stats_no_media']}</em>"

    # ---- General info ----
    mad_str, mad_cnt = stats["most_active"]
    if mad_str:
        try:
            mad_label = format_day_label(datetime.strptime(mad_str, "%Y-%m-%d"), lang=lang)
        except ValueError:
            mad_label = mad_str
    else:
        mad_label, mad_cnt = "N/A", 0

    total_days = len(stats["day_counts"])
    avg_day = real_total / total_days if total_days else 0
    total_media = sum(stats["media_counts"].values())

    gen_rows = (
        f'<div class="grow"><span>{t["stat_total_msgs"]}</span><strong>{real_total:,}</strong></div>'
        f'<div class="grow"><span>{t["stat_duration"]}</span><strong>{total_days} {t["stat_days"]}</strong></div>'
        f'<div class="grow"><span>{t["stat_avg_day"]}</span><strong>{avg_day:.0f} {t["stat_msgs_short"]}</strong></div>'
        f'<div class="grow"><span>{t["stat_media_count"]}</span><strong>{total_media:,}</strong></div>'
        f'<div class="grow"><span>{t["stat_most_active"]}</span><strong>{html.escape(mad_label)}</strong></div>'
        f'<div class="grow"><span>{t["stat_day_record"]}</span><strong>{mad_cnt:,} {t["stat_msgs_short"]}</strong></div>'
    )

    return f"""
<details class="stats-section">
  <summary>{t["stats_title"]}</summary>
  <div class="stats-grid">
    <div class="stats-box">
      <h3>{t["stats_messages"]}</h3>
      <div class="sender-bars">{sender_bars}</div>
    </div>
    <div class="stats-box">
      <h3>{t["stats_hourly"]}</h3>
      <div class="hour-chart">{hour_bars}</div>
    </div>
    <div class="stats-box">
      <h3>{t["stats_media"]}</h3>
      <div class="media-rows">{media_rows}</div>
    </div>
    <div class="stats-box">
      <h3>{t["stats_general"]}</h3>
      <div class="gen-rows">{gen_rows}</div>
    </div>
  </div>
</details>
"""
