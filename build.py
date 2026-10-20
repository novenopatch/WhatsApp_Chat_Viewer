#!/usr/bin/env python3
"""WhatsApp Chat Viewer

Convert WhatsApp chat export (.txt + media folder) into a modern,
responsive, and high-performance interactive HTML page.
"""

import gzip
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
    QUOTE_LINE_PATTERN,
    QUOTE_AUTHOR_PATTERN,
    EMOJI_PATTERN,
    REACTION_LINE_PATTERN,
    TRAILING_REACTION_PATTERN,
    DEFAULT_REACTION_EMOJIS,
)
from src.parser import (
    parse_date,
    format_day_label,
    get_attachment_filename,
    is_system_message,
    get_system_icon,
    get_media_type_label,
    format_inline_markdown,
    format_message,
    strip_annotations,
    iter_chat,
    parse_chat,
    parse_reaction_notification,
    extract_trailing_reactions,
    resolve_quote_target_id,
    process_chat_reactions,
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
    render_reactions_html,
    render_grouped_messages,
    build_html,
    minify_html,
    generate_thumbnails,
)
from src.config import (
    parse_dotenv as _parse_dotenv,
    find_chat_txt as _find_chat_txt,
    prompt_user as _prompt,
    parse_args,
    load_config,
)
from src.zip_handler import (
    extract_whatsapp_zip,
    is_zip_file,
    safe_extract_zip,
)


def main() -> None:
    """Main CLI execution flow."""
    cli_args = parse_args()
    if getattr(cli_args, "serve", False):
        from src.server import run_server
        run_server(host=cli_args.host, port=cli_args.port)
        return

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

    if getattr(cli_args, "thumbs", False) or os.environ.get("GENERATE_THUMBS"):
        print("🖼️  Génération des miniatures d'images...")
        num_thumbs = generate_thumbnails(media_dir)
        print(f"   Miniatures générées : {num_thumbs}")

    standalone = getattr(cli_args, "standalone", False)
    max_embed_bytes = getattr(cli_args, "max_embed_size", 20) * 1024 * 1024
    if standalone:
        print("📦 Mode Standalone activé : les médias sont intégrés en Base64 dans le HTML.")

    html_output = build_html(
        messages,
        media_dir,
        output_path=output_file,
        me_user=me_user,
        standalone=standalone,
        max_embed_size=max_embed_bytes,
    )
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)

    gz_output = output_file + ".gz"
    with gzip.open(gz_output, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(html_output)

    orig_kb = len(html_output.encode("utf-8")) / 1024
    gz_kb = os.path.getsize(gz_output) / 1024
    ratio = (1 - (gz_kb / orig_kb)) * 100 if orig_kb else 0
    print(f"✅ Fichier généré : {output_file}  ({len(messages):,} messages, {orig_kb:.1f} Ko)")
    print(f"📦 Version Gzip    : {gz_output}  ({gz_kb:.1f} Ko, -{ratio:.1f}%)")

    # Compression Brotli (optionnelle — nécessite `pip install brotli`)
    try:
        import brotli  # type: ignore
        html_bytes = html_output.encode("utf-8")
        br_output = output_file + ".br"
        with open(br_output, "wb") as f:
            f.write(brotli.compress(html_bytes, quality=11))
        br_kb = os.path.getsize(br_output) / 1024
        br_ratio = (1 - (br_kb / orig_kb)) * 100 if orig_kb else 0
        print(f"🗜️  Version Brotli  : {br_output}  ({br_kb:.1f} Ko, -{br_ratio:.1f}%)")
    except ImportError:
        pass  # brotli non installé — compression Gzip suffisante


if __name__ == "__main__":
    main()
