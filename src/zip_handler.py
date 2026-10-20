"""WhatsApp ZIP archive handler.

Extracts and detects WhatsApp chat files and media folders from exported .zip archives.
Provides military-grade Zip Slip & Zip Bomb (DoS) security validation and auto-discovery
of chat text files.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from src.constants import (
    MESSAGE_PATTERN,
    SYSTEM_MESSAGE_PATTERN,
    DEFAULT_MAX_ZIP_FILES,
    DEFAULT_MAX_UNCOMPRESSED_SIZE,
    DEFAULT_MAX_COMPRESSION_RATIO,
    DEFAULT_MIN_RATIO_THRESHOLD,
    WINDOWS_RESERVED_NAMES,
)


def is_zip_file(path: str | None) -> bool:
    """Return True if path points to an existing valid ZIP file."""
    if not path or not isinstance(path, str):
        return False
    clean_path = os.path.expanduser(path)
    if not os.path.isfile(clean_path):
        return False
    return zipfile.is_zipfile(clean_path)


def safe_extract_zip(
    zip_path: str,
    target_dir: str,
    max_total_size: int | None = None,
    max_files: int | None = None,
    max_ratio: float | None = None,
    min_ratio_threshold: int = DEFAULT_MIN_RATIO_THRESHOLD,
) -> list[str]:
    """Safely extract all files from a ZIP archive into target_dir.

    Protects against:
    1. Zip Slip (directory traversal attacks) by verifying:
       - Every extracted file and directory path stays strictly within target_dir.
       - No path components use '..' segments, colons, or embedded null bytes.
       - No symbolic links or hardlinks are followed or extracted.
       - Windows reserved device names (CON, PRN, AUX, etc.) are rejected.
    2. Zip Bombs & Decompression DoS (infinite size / extreme ratio) by verifying:
       - Total file count does not exceed max_files (default: 50,000).
       - No duplicate or overlapping local header offsets (anti-non-recursive zip bomb).
       - Declared total uncompressed size does not exceed max_total_size (default: 10 GiB).
       - Global declared expansion ratio does not exceed max_ratio (default: 100:1) on archives > 50 MiB uncompressed.
       - Extreme per-file compression ratio (> max_ratio) on files > 10 MiB.
       - Pre-flight free disk space check to prevent host storage exhaustion.
       - Real-time streaming byte and ratio guards to catch spoofed zip headers.
       - Immediate rollback/cleanup of all written files and empty folders on failure.
    """
    clean_zip = os.path.expanduser(zip_path)
    if not os.path.isfile(clean_zip):
        raise FileNotFoundError(f"Archive ZIP introuvable : {clean_zip}")

    zip_file_size = os.path.getsize(clean_zip)
    if zip_file_size == 0:
        raise ValueError("Sécurité : archive ZIP vide (0 octet)")

    if max_total_size is None:
        env_val = os.environ.get("MAX_UNCOMPRESSED_SIZE")
        max_total_size = int(env_val) if env_val and env_val.isdigit() else DEFAULT_MAX_UNCOMPRESSED_SIZE
    if max_files is None:
        env_val = os.environ.get("MAX_ZIP_FILES")
        max_files = int(env_val) if env_val and env_val.isdigit() else DEFAULT_MAX_ZIP_FILES
    if max_ratio is None:
        env_val = os.environ.get("MAX_COMPRESSION_RATIO")
        try:
            max_ratio = float(env_val) if env_val else DEFAULT_MAX_COMPRESSION_RATIO
        except ValueError:
            max_ratio = DEFAULT_MAX_COMPRESSION_RATIO

    abs_target = os.path.abspath(target_dir)
    os.makedirs(abs_target, exist_ok=True)

    extracted_files: list[str] = []
    created_dirs: list[str] = []
    current_dst: str | None = None
    total_extracted_bytes = 0
    chunk_size = 64 * 1024

    with zipfile.ZipFile(clean_zip, "r") as zf:
        members = zf.infolist()

        # Check 1: File count limit
        if len(members) > max_files:
            raise ValueError(
                f"Sécurité : archive suspecte (bombe zip potentielle) - "
                f"nombre excessif de fichiers : {len(members)} (limite : {max_files})"
            )

        # Check 2: Anti-non-recursive zip bomb (detect duplicate or overlapping local header offsets)
        seen_offsets: set[int] = set()
        for member in members:
            if member.header_offset in seen_offsets:
                raise ValueError(
                    f"Sécurité : bombe zip suspectée (en-têtes locaux dupliqués à l'offset {member.header_offset})"
                )
            seen_offsets.add(member.header_offset)

        # Verify physical ordering: members must not overlap their compressed payloads
        sorted_members = sorted(members, key=lambda m: m.header_offset)
        for i in range(len(sorted_members) - 1):
            m1 = sorted_members[i]
            m2 = sorted_members[i + 1]
            fn_len = len(m1.filename.encode("utf-8", "replace"))
            min_next_offset = m1.header_offset + 30 + fn_len + max(0, m1.compress_size)
            if m2.header_offset < min_next_offset:
                raise ValueError(
                    f"Sécurité : bombe zip suspectée (chevauchement physique des données "
                    f"entre '{m1.filename}' et '{m2.filename}')"
                )

        # Check 3: Declared sizes and compression ratio
        total_declared_size = 0
        for member in members:
            if member.file_size < 0 or member.compress_size < 0:
                raise ValueError(f"Sécurité : taille négative invalide pour '{member.filename}'")

            total_declared_size += member.file_size

            # Per-file compression ratio check on files > 10 MiB
            if member.file_size > 10 * 1024 * 1024:
                if member.compress_size <= 0:
                    raise ValueError(
                        f"Sécurité : bombe zip suspectée - taille compressée nulle ou anormale "
                        f"pour '{member.filename}'"
                    )
                ratio = member.file_size / member.compress_size
                if ratio > max_ratio:
                    raise ValueError(
                        f"Sécurité : bombe zip suspectée - ratio de compression anormal "
                        f"({ratio:.1f}:1) pour '{member.filename}' (limite : {max_ratio}:1)"
                    )

        if total_declared_size > max_total_size:
            raise ValueError(
                f"Sécurité : archive suspecte (bombe zip potentielle) - "
                f"taille totale déclarée excessive : {total_declared_size} octets "
                f"(limite : {max_total_size} octets)"
            )

        # Global compression ratio check against actual zip archive size
        max_safe_global = max(int(zip_file_size * max_ratio), min_ratio_threshold)
        if total_declared_size > max_safe_global:
            global_ratio = total_declared_size / max(zip_file_size, 1)
            raise ValueError(
                f"Sécurité : bombe zip suspectée - ratio global de décompression anormal "
                f"({global_ratio:.1f}:1) pour l'archive entière (limite : {max_ratio}:1)"
            )

        # Check 4: Pre-flight free disk space check
        try:
            free_disk = shutil.disk_usage(abs_target).free
            # Reserve at least declared size + 50 MiB margin
            if total_declared_size + (50 * 1024 * 1024) > free_disk:
                raise OSError(
                    f"Espace disque insuffisant sur {abs_target} : "
                    f"{free_disk / (1024**2):.1f} Mo libres, "
                    f"au moins {(total_declared_size + 50 * 1024 * 1024) / (1024**2):.1f} Mo requis."
                )
        except OSError as e:
            if "Espace disque insuffisant" in str(e):
                raise
            # If disk_usage is not supported on current platform/fs, proceed

        # Check 5: Member sanitization, Zip Slip check, and streaming extraction
        try:
            for member in members:
                # 5a: Path content sanitization
                if "\0" in member.filename:
                    raise ValueError(f"Sécurité : octet nul interdit dans le nom de fichier : {member.filename!r}")

                if ":" in member.filename:
                    raise ValueError(f"Sécurité : caractère deux-points interdit dans le nom : {member.filename}")

                # 5b: Windows reserved device names
                parts = member.filename.replace("\\", "/").split("/")
                for part in parts:
                    stem = part.split(".")[0].upper()
                    if stem in WINDOWS_RESERVED_NAMES:
                        raise ValueError(f"Sécurité : nom de périphérique réservé Windows interdit : {part}")

                # 5c: Prohibit symbolic links and special device nodes
                unix_mode = (member.external_attr >> 16) & 0o170000
                if unix_mode == 0o120000:
                    raise ValueError(f"Sécurité : lien symbolique interdit dans l'archive : '{member.filename}'")
                if unix_mode in (0o010000, 0o020000, 0o060000, 0o140000):
                    raise ValueError(f"Sécurité : type de fichier spécial non autorisé : '{member.filename}'")

                # 5d: Zip Slip & Directory traversal protection
                norm_name = os.path.normpath(member.filename)
                if norm_name.startswith("..") or os.path.isabs(norm_name):
                    raise ValueError(f"Sécurité : tentative de Zip Slip détectée pour '{member.filename}'")

                dest_path = os.path.abspath(os.path.join(abs_target, member.filename))

                # Skip root target dir itself if referenced as member
                if dest_path == abs_target:
                    continue

                try:
                    common = os.path.commonpath([abs_target, dest_path])
                except ValueError:
                    raise ValueError(f"Sécurité : tentative de Zip Slip détectée pour '{member.filename}'")

                if common != abs_target:
                    raise ValueError(f"Sécurité : tentative de Zip Slip détectée pour '{member.filename}'")

                # Ensure no symlinks exist along the target path
                if os.path.islink(dest_path):
                    raise ValueError(f"Sécurité : la destination '{dest_path}' est un lien symbolique existant")

                curr_dir = os.path.dirname(dest_path)
                while curr_dir and len(curr_dir) >= len(abs_target):
                    if os.path.islink(curr_dir):
                        raise ValueError(f"Sécurité : dossier parent '{curr_dir}' est un lien symbolique")
                    if curr_dir == abs_target:
                        break
                    parent = os.path.dirname(curr_dir)
                    if parent == curr_dir:
                        break
                    curr_dir = parent

                if member.is_dir() or member.filename.endswith("/"):
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path, exist_ok=True)
                        created_dirs.append(dest_path)
                    continue

                # Ensure parent directories exist
                parent_dir = os.path.dirname(dest_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                    created_dirs.append(parent_dir)

                # 5e: Stream extraction with real-time guards against spoofed zip bombs
                current_dst = dest_path
                member_extracted_bytes = 0

                with zf.open(member, "r") as src, open(dest_path, "wb") as dst:
                    while True:
                        chunk = src.read(chunk_size)
                        if not chunk:
                            break
                        chunk_len = len(chunk)
                        total_extracted_bytes += chunk_len
                        member_extracted_bytes += chunk_len

                        # Real-time guard: global size limit
                        if total_extracted_bytes > max_total_size:
                            raise ValueError(
                                f"Sécurité : bombe zip détectée ! La décompression réelle a "
                                f"dépassé la limite autorisée de {max_total_size} octets."
                            )

                        # Real-time guard: global ratio expansion
                        if total_extracted_bytes > max_safe_global:
                            raise ValueError(
                                f"Sécurité : bombe zip détectée ! Le volume décompressé dépasse "
                                f"le ratio maximum autorisé ({max_ratio}:1) par rapport à l'archive."
                            )

                        # Real-time guard: spoofed member size (anti-header forging)
                        if member.file_size > 0 and member_extracted_bytes > member.file_size:
                            raise ValueError(
                                f"Sécurité : bombe zip suspectée (taille réelle supérieure "
                                f"à la taille déclarée pour '{member.filename}')"
                            )

                        # Real-time guard: per-member ratio on large streaming
                        if member.compress_size > 0 and member_extracted_bytes > min_ratio_threshold:
                            member_ratio = member_extracted_bytes / member.compress_size
                            if member_ratio > max_ratio:
                                raise ValueError(
                                    f"Sécurité : bombe zip détectée ! Ratio anormal ({member_ratio:.1f}:1) "
                                    f"en cours de décompression pour '{member.filename}'."
                                )

                        dst.write(chunk)

                # Verify declared empty file was actually empty
                if member.file_size == 0 and member_extracted_bytes > 0:
                    raise ValueError(
                        f"Sécurité : fichier déclaré vide '{member.filename}' mais contient des données décompressées"
                    )

                extracted_files.append(dest_path)
                current_dst = None

        except Exception:
            # Clean up active partial file and all previously extracted files on failure
            if current_dst and (os.path.isfile(current_dst) or os.path.islink(current_dst)):
                try:
                    os.remove(current_dst)
                except OSError:
                    pass
            for path in extracted_files:
                if os.path.isfile(path) or os.path.islink(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            for d in reversed(created_dirs):
                try:
                    if os.path.isdir(d) and not os.listdir(d):
                        os.rmdir(d)
                except OSError:
                    pass
            raise

    return extracted_files


def _is_whatsapp_txt(file_path: str) -> bool:
    """Check if the given text file looks like a WhatsApp chat export."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in range(50):
                line = f.readline()
                if not line:
                    break
                if MESSAGE_PATTERN.search(line) or SYSTEM_MESSAGE_PATTERN.search(line):
                    return True
    except OSError:
        pass
    return False


def find_chat_in_extracted(extracted_dir: str) -> tuple[str, str]:
    """Find the WhatsApp chat .txt file and media folder inside an extracted directory.

    Returns (chat_file_path, media_dir_path).
    Raises FileNotFoundError if no suitable chat .txt file is found.
    """
    abs_dir = os.path.abspath(extracted_dir)
    candidates: list[str] = []

    for root, _, files in os.walk(abs_dir):
        for f in files:
            if f.lower().endswith(".txt"):
                candidates.append(os.path.join(root, f))

    if not candidates:
        raise FileNotFoundError(f"Aucun fichier .txt de discussion trouvé dans : {extracted_dir}")

    # Prioritize standard WhatsApp naming conventions
    best_chat: str | None = None
    for cand in candidates:
        fname = os.path.basename(cand).lower()
        if fname in ("_chat.txt", "chat.txt"):
            best_chat = cand
            break
        if "whatsapp" in fname:
            best_chat = cand
            break

    # If no standard name, verify content with regex
    if not best_chat:
        for cand in candidates:
            if _is_whatsapp_txt(cand):
                best_chat = cand
                break

    # Fallback to the first .txt file
    if not best_chat:
        best_chat = candidates[0]

    # Locate media directory
    chat_dir = os.path.dirname(best_chat)
    sub_media = os.path.join(chat_dir, "media")
    root_media = os.path.join(abs_dir, "media")

    if os.path.isdir(sub_media):
        media_dir = sub_media
    elif os.path.isdir(root_media):
        media_dir = root_media
    else:
        # WhatsApp usually exports media directly alongside the .txt file
        media_dir = chat_dir

    return best_chat, media_dir


def extract_whatsapp_zip(
    zip_path: str,
    extract_dir: str | None = None,
    max_total_size: int | None = None,
    max_files: int | None = None,
    max_ratio: float | None = None,
) -> tuple[str, str]:
    """High-level function: extract a WhatsApp ZIP export and return (chat_file, media_dir)."""
    clean_zip = os.path.expanduser(zip_path)
    if not os.path.isfile(clean_zip):
        raise FileNotFoundError(f"Archive ZIP introuvable : {zip_path}")

    if not extract_dir:
        base_name, _ = os.path.splitext(os.path.abspath(clean_zip))
        extract_dir = base_name

    print(f"📦 Archive ZIP WhatsApp détectée : {clean_zip}")
    print(f"📂 Extraction vers : {extract_dir} …")
    safe_extract_zip(
        clean_zip,
        extract_dir,
        max_total_size=max_total_size,
        max_files=max_files,
        max_ratio=max_ratio,
    )

    chat_file, media_dir = find_chat_in_extracted(extract_dir)
    print(f"  ✓ Chat trouvé  : {chat_file}")
    print(f"  ✓ Médias       : {media_dir}")

    return chat_file, media_dir
