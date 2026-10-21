#!/usr/bin/env python3
"""WhatsApp Chat Viewer

Convert WhatsApp chat export (.txt + media folder) into a modern,
responsive, and high-performance interactive HTML page.
"""

from __future__ import annotations

import cProfile
import gzip
import logging
import os
import sys

# Ensure UTF-8 output on all platforms (especially Windows cmd.exe / PowerShell)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src import __version__
from src.logging_config import setup_logging, get_logger

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
from src.hash_validator import HashRegistry


def main() -> None:
    """Main CLI execution flow."""
    from src.monitor import PerformanceTracker

    cli_args = parse_args()
    verbose = getattr(cli_args, "verbose", False)
    ultra_perf = getattr(cli_args, "ultra_perf", False)
    profile_mode = getattr(cli_args, "profile", False)

    # Setup logging
    setup_logging(verbose=verbose)
    logger = get_logger(__name__)

    # Initialize profiler if profiling mode is enabled
    profiler = None
    if profile_mode:
        logger.info("Profiling mode enabled - profiling with cProfile")
        profiler = cProfile.Profile()
        profiler.enable()

    logger.info(f"WhatsApp Chat Viewer v{__version__}")
    if ultra_perf:
        logger.info("  ⚡ Mode Ultra-Performance activé")
    if verbose:
        logger.debug("  🔍 Mode Verbeux activé")

    if getattr(cli_args, "serve", False):
        from src.server import run_server
        run_server(
            host=cli_args.host,
            port=cli_args.port,
            verbose=verbose,
            ultra_perf=ultra_perf,
        )
        return

    tracker = PerformanceTracker("Build CLI")

    chat_file, media_dir, output_file, me_user, hash_registry = load_config()

    dotenv_path = os.path.join(os.getcwd(), ".env")
    env = _parse_dotenv(dotenv_path) if os.path.isfile(dotenv_path) else {}
    raw_lang = getattr(cli_args, "lang", None) or env.get("LANG") or env.get("LANGUAGE") or "auto"
    from src.i18n import resolve_language
    lang = resolve_language(raw_lang)

    logger.info(f"Configuration:")
    logger.info(f"  chat    → {chat_file}")
    logger.info(f"  médias  → {media_dir}")
    logger.info(f"  sortie  → {output_file}")
    logger.info(f"  langue  → {lang}")
    if me_user:
        logger.info(f"  moi     → {me_user}")

    if not os.path.isfile(chat_file):
        logger.error(f"Fichier introuvable : {chat_file}")
        sys.exit(1)

    # Verify hashes if --verify-hashes was enabled
    if hash_registry:
        logger.info("Vérification de l'intégrité des fichiers extraits (SHA-256)...")
        verification_results = hash_registry.verify_all()
        failed_files = [path for path, verified in verification_results.items() if not verified]
        if failed_files:
            logger.warning(f"Échec de vérification pour {len(failed_files)} fichiers")
            for failed in failed_files[:5]:
                logger.warning(f"  - {failed}")
            if len(failed_files) > 5:
                logger.warning(f"  ... et {len(failed_files) - 5} autres")
        else:
            logger.info(f"✓ Tous les {len(verification_results)} fichiers vérifiés avec succès")
        logger.info(hash_registry.get_report())

    messages = parse_chat(chat_file)
    if not messages:
        logger.warning("Aucun message trouvé. Vérifiez le fichier de chat.")
        sys.exit(1)

    step_parse = tracker.mark_step("parsing")
    logger.debug(f"Parsing : {len(messages):,} messages en {step_parse['elapsed_s']:.2f}s | RAM: {step_parse['ram_rss_mb']:.1f} Mo | CPU user: {step_parse['cpu_user_s']:.2f}s")

    attendees = list(dict.fromkeys(msg["sender"] for msg in messages))
    if not me_user:
        context_hint = f"{chat_file} {os.getcwd()}"
        detected_me = auto_detect_me(attendees, context_hint=context_hint)
        if detected_me:
            me_user = detected_me
            logger.info(f"Interlocuteur 'Moi' auto-détecté : {me_user}")
    else:
        resolved = resolve_me_user(me_user, attendees)
        if resolved:
            me_user = resolved
            logger.info(f"Interlocuteur 'Moi' configuré : {me_user}")
        else:
            logger.warning(f"'{me_user}' n'a pas été trouvé parmi les participants : {', '.join(attendees)}")

    if getattr(cli_args, "thumbs", False) or os.environ.get("GENERATE_THUMBS"):
        logger.info("Génération des miniatures d'images...")
        num_thumbs = generate_thumbnails(media_dir)
        step_thumbs = tracker.mark_step("thumbnails")
        logger.info(f"Miniatures générées : {num_thumbs}")
        logger.debug(f"Miniatures : {step_thumbs['elapsed_s']:.2f}s | RAM: {step_thumbs['ram_rss_mb']:.1f} Mo")

    standalone = getattr(cli_args, "standalone", False)
    max_embed_bytes = getattr(cli_args, "max_embed_size", 20) * 1024 * 1024
    if standalone:
        logger.info("Mode Standalone activé : intégration des médias en Base64 dans le HTML.")

    html_output = build_html(
        messages,
        media_dir,
        output_path=output_file,
        me_user=me_user,
        standalone=standalone,
        max_embed_size=max_embed_bytes,
        lang=lang,
    )
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)

    step_render = tracker.mark_step("rendering")
    logger.debug(f"Rendu HTML : {step_render['elapsed_s']:.2f}s | RAM: {step_render['ram_rss_mb']:.1f} Mo | CPU user: {step_render['cpu_user_s']:.2f}s")

    gz_output = output_file + ".gz"
    with gzip.open(gz_output, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(html_output)

    orig_kb = len(html_output.encode("utf-8")) / 1024
    gz_kb = os.path.getsize(gz_output) / 1024
    ratio = (1 - (gz_kb / orig_kb)) * 100 if orig_kb else 0
    logger.info(f"Fichier généré  : {output_file}  ({len(messages):,} messages, {orig_kb:.1f} Ko)")
    logger.info(f"  └─ Gzip         : {gz_output}  ({gz_kb:.1f} Ko, -{ratio:.1f}%)")

    # Compression Brotli (optionnelle — nécessite `pip install brotli`)
    try:
        import brotli  # type: ignore
        html_bytes = html_output.encode("utf-8")
        br_output = output_file + ".br"
        with open(br_output, "wb") as f:
            f.write(brotli.compress(html_bytes, quality=11))
        br_kb = os.path.getsize(br_output) / 1024
        br_ratio = (1 - (br_kb / orig_kb)) * 100 if orig_kb else 0
        logger.info(f"  └─ Brotli       : {br_output}  ({br_kb:.1f} Ko, -{br_ratio:.1f}%)")
    except ImportError:
        logger.debug("brotli non installé — compression Gzip suffisante")

    final = tracker.finish()
    logger.info(f"Métriques de performance :")
    logger.info(f"   Durée totale : {final['elapsed_s']:.2f}s")
    logger.info(f"   RAM RSS      : {final['ram_rss_mb']:.1f} Mo (pic: {final['peak_ram_mb']:.1f} Mo)")
    logger.info(f"   CPU user     : {final['cpu_user_s']:.2f}s (sys: {final['cpu_sys_s']:.2f}s, {final['cpu_percent']:.1f}%)")

    # Save profiling stats if enabled
    if profile_mode and profiler:
        profiler.disable()
        profiler.dump_stats("profile.stats")
        logger.info("Profiling stats saved to profile.stats")
        logger.info("View with: python -m pstats profile.stats")
        logger.info("Then use: sort cumtime, stats 20")


if __name__ == "__main__":
    main()
