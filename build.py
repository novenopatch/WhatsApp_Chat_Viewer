#!/usr/bin/env python3
"""WhatsApp Chat Viewer

Convert WhatsApp chat export (.txt + media folder) into a modern,
responsive, and high-performance interactive HTML page.
"""

import os
import sys

# Re-export key functions and constants for backward compatibility
from src.constants import (
    MESSAGE_PATTERN as message_pattern,
    ATTACHMENT_KEYWORDS,
    DATE_FORMATS,
    AVATAR_COLORS,
    FRENCH_MONTHS,
    SYSTEM_MESSAGE_PATTERN,
    SYSTEM_ICONS,
    MEDIA_TYPE_MAP,
)
from src.parser import (
    parse_date,
    format_day_label,
    get_attachment_filename,
    is_system_message,
    get_system_icon,
    get_media_type_label,
    format_message,
    strip_annotations,
    parse_chat,
)
from src.stats import (
    compute_stats,
    render_stats_html,
)
from src.user_detector import (
    resolve_me_user,
    auto_detect_me,
)
from src.renderer import (
    render_attachment,
    build_bubble as _build_bubble,
    render_grouped_messages,
    build_html,
)
from src.config import (
    parse_dotenv as _parse_dotenv,
    find_chat_txt as _find_chat_txt,
    prompt_user as _prompt,
    parse_args,
    load_config,
)


def main() -> None:
    """Main CLI execution flow."""
    chat_file, media_dir, output_file, me_user = load_config()

    print(f"\n  chat    → {chat_file}")
    print(f"  médias  → {media_dir}")
    print(f"  sortie  → {output_file}")
    if me_user:
        print(f"  moi     → {me_user}")
    print()

    if not os.path.isfile(chat_file):
        print(f"❌ Fichier introuvable : {chat_file}")
        sys.exit(1)

    messages = parse_chat(chat_file)
    if not messages:
        print("⚠️  Aucun message trouvé. Vérifiez le fichier de chat.")
        sys.exit(1)

    attendees = list(dict.fromkeys(msg["sender"] for msg in messages))
    if not me_user:
        context_hint = f"{chat_file} {os.getcwd()}"
        detected_me = auto_detect_me(attendees, context_hint=context_hint)
        if detected_me:
            me_user = detected_me
            print(f"💡 Interlocuteur 'Moi' auto-détecté : {me_user}")
    else:
        resolved = resolve_me_user(me_user, attendees)
        if resolved:
            me_user = resolved
            print(f"👤 Interlocuteur 'Moi' configuré : {me_user}")
        else:
            print(f"⚠️  '{me_user}' n'a pas été trouvé parmi les participants : {', '.join(attendees)}")

    html_output = build_html(messages, media_dir, output_path=output_file, me_user=me_user)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"✅ Fichier généré : {output_file}  ({len(messages):,} messages)")


if __name__ == "__main__":
    main()
