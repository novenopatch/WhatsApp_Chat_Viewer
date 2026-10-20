"""Configuration loader supporting CLI args, .env file, defaults, and interactive prompts."""

import argparse
import os
from src import __version__
from src.zip_handler import is_zip_file, extract_whatsapp_zip


def parse_dotenv(path: str) -> dict[str, str]:
    """Minimal .env parser with zero external dependencies.

    Supports KEY=value, KEY="value", KEY='value', and # comments.
    """
    env: dict[str, str] = {}
    if not os.path.isfile(path):
        return env
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def find_chat_txt(directory: str) -> str | None:
    """Auto-discover the WhatsApp chat .txt inside directory."""
    if not os.path.isdir(directory):
        return None
    for name in ("_chat.txt", "chat.txt"):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    for entry in sorted(os.listdir(directory)):
        if entry.endswith(".txt"):
            return os.path.join(directory, entry)
    return None


def prompt_user(label: str, default: str = "") -> str:
    """Ask the user for a value with tab-completion when available."""
    import sys
    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        return default
    try:
        import readline
        readline.set_completer_delims(" \t\n")
        readline.parse_and_bind("tab: complete")
    except ImportError:
        pass
    hint = f"  [{default}]" if default else ""
    try:
        value = input(f"  {label}{hint} : ").strip()
    except (EOFError, OSError, KeyboardInterrupt):
        return default
    return value if value else default



def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(
        prog="build.py",
        description="Convertit un export WhatsApp (.txt ou .zip) en page HTML interactive et moderne.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python3 build.py mon_export.zip\n"
            "  python3 build.py --zip export.zip --output chat.html\n"
            "  python3 build.py --dir ~/exports/WhatsApp_Export/\n"
            "  python3 build.py --chat chat.txt --media media/ --output chat.html --me \"Mon Nom\"\n"
            "\n"
            "Sans argument, le script lit .env puis les valeurs par défaut,\n"
            "et pose les questions manquantes de façon interactive."
        ),
    )
    p.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Affiche le numéro de version et quitte",
    )
    p.add_argument("input_target", nargs="?", help="Fichier .zip, .txt ou dossier d'export WhatsApp")
    p.add_argument("--zip", "-z", metavar="FILE", help="Archive .zip d'export WhatsApp (auto-extraction et détection)")
    p.add_argument("--extract-dir", metavar="DIR", help="Dossier cible pour l'extraction de l'archive ZIP (défaut : dossier au nom de l'archive)")
    p.add_argument("--chat", "-c", metavar="FILE", help="Fichier de chat .txt")
    p.add_argument("--dir", "-d", metavar="DIR", help="Dossier d'export WhatsApp complet (auto-détection du .txt et media/)")
    p.add_argument("--media", "-m", metavar="DIR", help="Dossier des médias")
    p.add_argument("--output", "-o", metavar="FILE", help="Fichier HTML de sortie (défaut : output.html)")
    p.add_argument("--me", "--your-name", dest="me", metavar="NAME", help="Votre nom ou pseudo dans la conversation (bulles à droite sur fond vert)")
    p.add_argument("--thumbs", action="store_true", help="Génère des miniatures légères pour les photos afin d'accélérer le rendu")
    p.add_argument("--standalone", "--embed", action="store_true", dest="standalone", help="Intègre les images et médias en Base64 pour produire un unique fichier HTML autonome")
    p.add_argument("--max-embed-size", type=int, default=20, metavar="MB", help="Taille max en Mo par média intégré en mode standalone (défaut : 20)")
    p.add_argument("--serve", action="store_true", help="Lance un serveur Web local avec interface Drag & Drop (ex: http://127.0.0.1:8080)")
    p.add_argument("--port", type=int, default=8080, help="Port pour le serveur Web --serve (défaut : 8080)")
    p.add_argument("--host", default="127.0.0.1", help="Hôte d'écoute pour le serveur Web --serve (défaut : 127.0.0.1)")
    return p.parse_args(args)


def load_config(cli_args: list[str] | None = None) -> tuple[str, str, str, str | None]:
    """Resolve (chat_file, media_dir, output_file, me_user) using a 4-tier hierarchy:

    1. CLI arguments  (--zip / input_target / --chat / --dir / --media / --output / --me)
    2. .env file      (ZIP_FILE / CHAT_FILE / CHAT_DIR / MEDIA_DIR / OUTPUT_FILE / ME / YOUR_NAME)
    3. Defaults       (chat.txt / candidate .zip + media/ in current directory if present)
    4. Interactive    (prompt user for remaining missing info)
    """
    args = parse_args(cli_args)

    chat_file: str | None = None
    media_dir: str | None = None
    output_file: str | None = None
    me_user: str | None = None

    # Tier 1 — CLI args
    target_zip = args.zip
    if not target_zip and args.input_target and is_zip_file(args.input_target):
        target_zip = args.input_target
    elif not target_zip and args.chat and is_zip_file(args.chat):
        target_zip = args.chat
    elif not target_zip and args.dir and is_zip_file(args.dir):
        target_zip = args.dir

    if target_zip:
        chat_file, media_dir = extract_whatsapp_zip(target_zip, args.extract_dir)

    # Handle input_target if not a zip
    if chat_file is None and args.input_target:
        inp = os.path.expanduser(args.input_target)
        if os.path.isdir(inp):
            found = find_chat_txt(inp)
            if found:
                chat_file = found
                candidate = os.path.join(inp, "media")
                media_dir = candidate if os.path.isdir(candidate) else inp
        elif os.path.isfile(inp) and inp.lower().endswith(".txt"):
            chat_file = inp

    if chat_file is None and args.dir:
        d = os.path.expanduser(args.dir)
        if os.path.isdir(d):
            found = find_chat_txt(d)
            if found:
                chat_file = found
                candidate = os.path.join(d, "media")
                media_dir = candidate if os.path.isdir(candidate) else d
                print(f"• Dossier CLI détecté : {d}")
            else:
                print(f"! Aucun fichier .txt trouvé dans : {d}")
        else:
            print(f"! Dossier introuvable : {d}")

    if chat_file is None and args.chat:
        chat_file = os.path.expanduser(args.chat)

    if args.media:
        media_dir = os.path.expanduser(args.media)
    if args.output:
        output_file = os.path.expanduser(args.output)
    if args.me:
        me_user = args.me

    # Tier 2 — .env file
    dotenv_path = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(dotenv_path):
        env = parse_dotenv(dotenv_path)
        print("• Fichier .env détecté → lecture de la configuration…")

        if chat_file is None:
            zip_env = env.get("ZIP_FILE", "").strip()
            if zip_env and is_zip_file(zip_env):
                chat_file, media_dir = extract_whatsapp_zip(zip_env, env.get("EXTRACT_DIR"))

        if chat_file is None:
            chat_dir = env.get("CHAT_DIR", "").strip()
            if chat_dir and os.path.isdir(chat_dir):
                found = find_chat_txt(chat_dir)
                if found:
                    chat_file = found
                    if media_dir is None:
                        candidate = os.path.join(chat_dir, "media")
                        media_dir = candidate if os.path.isdir(candidate) else chat_dir
            elif env.get("CHAT_FILE"):
                candidate_cf = env["CHAT_FILE"]
                if is_zip_file(candidate_cf):
                    chat_file, media_dir = extract_whatsapp_zip(candidate_cf, env.get("EXTRACT_DIR"))
                else:
                    chat_file = candidate_cf

        if media_dir is None and env.get("MEDIA_DIR"):
            media_dir = env["MEDIA_DIR"]
        if output_file is None and env.get("OUTPUT_FILE"):
            output_file = env["OUTPUT_FILE"]
        if me_user is None:
            me_user = env.get("ME") or env.get("YOUR_NAME")

    # Tier 3 — Defaults (CWD)
    if chat_file is None:
        default_chat = os.path.join(os.getcwd(), "chat.txt")
        if os.path.isfile(default_chat):
            chat_file = default_chat
            print(f"📁 Fichier trouvé par défaut : {default_chat}")
        else:
            # Check for candidate WhatsApp zip file in current directory
            zips = [f for f in sorted(os.listdir(os.getcwd())) if f.lower().endswith(".zip") and not f.startswith(".")]
            whatsapp_zips = [f for f in zips if "whatsapp" in f.lower()]
            cand_zip = whatsapp_zips[0] if whatsapp_zips else (zips[0] if len(zips) == 1 else None)
            if cand_zip:
                zip_full = os.path.join(os.getcwd(), cand_zip)
                if is_zip_file(zip_full):
                    chat_file, media_dir = extract_whatsapp_zip(zip_full)

    if media_dir is None:
        default_media = os.path.join(os.getcwd(), "media")
        if os.path.isdir(default_media):
            media_dir = default_media

    if output_file is None:
        output_file = os.path.join(os.getcwd(), "output.html")

    # Tier 4 — Interactive prompt
    if chat_file is None:
        print("\n🔍 Aucune configuration automatique trouvée.")
        print("   Astuce : créez un .env (voir .env.example) ou utilisez --zip / --dir / --chat.\n")
        chat_file = prompt_user(
            "Chemin du fichier de chat (.txt ou .zip)",
            os.path.join(os.getcwd(), "chat.txt"),
        )
        if chat_file and is_zip_file(chat_file):
            chat_file, extracted_media = extract_whatsapp_zip(chat_file)
            if media_dir is None:
                media_dir = extracted_media

    if media_dir is None:
        guess = os.path.join(os.path.dirname(os.path.abspath(chat_file)), "media")
        if not os.path.isfile(chat_file) or args.chat or args.dir or getattr(args, "zip", None):
            media_dir = guess
        else:
            print(f"\n📂 Dossier des médias introuvable automatiquement.")
            media_dir = prompt_user("Dossier des médias (Entrée pour ignorer)", guess)

    return chat_file, media_dir, output_file, me_user
