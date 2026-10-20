"""Lightweight local web server with drag & drop conversion interface."""

from __future__ import annotations

import base64
import http.server
import json
import os
import re
import shutil
import tempfile
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse, unquote
import uuid
import webbrowser

from src.monitor import PerformanceTracker, get_ram_rss_mb, get_peak_ram_mb, get_cpu_times
from src.parser import parse_chat
from src.renderer import build_html, generate_thumbnails, load_template_file, MIME_MAP
from src.user_detector import auto_detect_me, resolve_me_user
from src.zip_handler import extract_whatsapp_zip

# Active conversion sessions: session_id -> {html_path, media_dir, tmp_dir}
SESSIONS: dict[str, dict[str, str]] = {}

# Active conversion tasks progress: task_id -> {phase, percent, files_extracted, total_files, ...}
PROGRESS_TASKS: dict[str, dict[str, Any]] = {}
PROGRESS_LOCK = threading.Lock()

# Server runtime mode flags
SERVER_VERBOSE: bool = False
SERVER_ULTRA_PERF: bool = False


def get_session_base_dir() -> str:
    """Return an on-disk directory for storing session files (avoiding tmpfs/RAM)."""
    env_dir = os.environ.get("WA_SESSION_DIR") or os.environ.get("WA_TEMP_DIR")
    if env_dir:
        os.makedirs(env_dir, exist_ok=True)
        return env_dir

    # Prefer ~/.cache/whatsapp_chat_viewer/sessions on physical disk
    cache_base = os.path.expanduser("~/.cache/whatsapp_chat_viewer/sessions")
    try:
        os.makedirs(cache_base, exist_ok=True)
        test_file = os.path.join(cache_base, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return cache_base
    except OSError:
        pass

    # Fallback to local .temp_sessions in current working directory
    local_temp = os.path.abspath(".temp_sessions")
    try:
        os.makedirs(local_temp, exist_ok=True)
        return local_temp
    except OSError:
        return tempfile.gettempdir()


def cleanup_stale_sessions() -> None:
    """Clean up leftover session folders from previously killed processes."""
    base_dir = get_session_base_dir()
    if not os.path.isdir(base_dir):
        return
    for item in os.listdir(base_dir):
        if item.startswith("wa_session_"):
            full = os.path.join(base_dir, item)
            try:
                if os.path.isdir(full):
                    shutil.rmtree(full, ignore_errors=True)
            except OSError:
                pass


def extract_boundary(content_type: str) -> str | None:
    """Extract boundary string from multipart/form-data Content-Type header."""
    if not content_type:
        return None
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            b = part[len("boundary="):].strip()
            if b.startswith('"') and b.endswith('"'):
                b = b[1:-1]
            return b
    return None


def parse_multipart_stream(
    stream,
    content_length: int,
    boundary: str | bytes,
    target_dir: str,
    chunk_size: int = 1024 * 1024,
    progress_callback: Any = None,
) -> tuple[dict[str, str], str | None, str | None, int]:
    """Stream multipart form-data directly to disk without holding files in RAM.

    Returns:
        (fields_dict, saved_file_path, original_filename, file_bytes_written)
    """
    if isinstance(boundary, str):
        boundary_bytes = boundary.encode("latin1")
    else:
        boundary_bytes = boundary

    marker = b"--" + boundary_bytes
    delim = b"\r\n--" + boundary_bytes
    carry_len = len(delim) + 4

    fields: dict[str, str] = {}
    saved_file_path: str | None = None
    saved_file_name: str | None = None
    file_bytes_written = 0

    bytes_left = content_length
    buf = bytearray()
    total_bytes_read = 0

    def read_more() -> bytes:
        nonlocal bytes_left, total_bytes_read
        if bytes_left <= 0:
            return b""
        to_read = min(chunk_size, bytes_left)
        chunk = stream.read(to_read)
        if not chunk:
            bytes_left = 0
            return b""
        bytes_left -= len(chunk)
        total_bytes_read += len(chunk)
        if progress_callback:
            progress_callback(total_bytes_read, content_length)
        return chunk

    # Read until the initial marker (--boundary)
    while True:
        idx = buf.find(marker)
        if idx != -1:
            eol = buf.find(b"\r\n", idx + len(marker))
            if eol != -1:
                del buf[:eol + 2]
                break
        chunk = read_more()
        if not chunk:
            break
        buf.extend(chunk)

    while True:
        # Check if we hit the closing boundary marker (--boundary--)
        if buf.startswith(b"--"):
            break

        # Read headers for the current part
        while b"\r\n\r\n" not in buf:
            chunk = read_more()
            if not chunk:
                break
            buf.extend(chunk)

        hdr_end = buf.find(b"\r\n\r\n")
        if hdr_end == -1:
            break

        headers_raw = bytes(buf[:hdr_end]).decode("latin1", errors="replace")
        del buf[:hdr_end + 4]

        # Extract name and filename from Content-Disposition
        part_name = None
        part_filename = None

        disp_match = re.search(r"Content-Disposition:\s*form-data;\s*([^\r\n]+)", headers_raw, re.IGNORECASE)
        if disp_match:
            params = disp_match.group(1)
            name_m = re.search(r'name=(?:"([^"]+)"|([^\s;]+))', params, re.IGNORECASE)
            if name_m:
                part_name = name_m.group(1) or name_m.group(2)
            fn_m = re.search(r'filename=(?:"([^"]+)"|([^\s;]+))', params, re.IGNORECASE)
            if fn_m:
                part_filename = os.path.basename(fn_m.group(1) or fn_m.group(2))

        is_file = bool(part_filename) or (part_name == "zip_file")
        out_f = None
        if is_file:
            saved_file_name = part_filename or "export.zip"
            saved_file_path = os.path.join(target_dir, saved_file_name)
            out_f = open(saved_file_path, "wb")
        val_buf = bytearray() if not is_file else None

        # Stream content of part until next delimiter: \r\n--boundary
        while True:
            d_idx = buf.find(delim)
            if d_idx != -1:
                # Delimiter found!
                data_slice = buf[:d_idx]
                if is_file and out_f:
                    out_f.write(data_slice)
                    file_bytes_written += len(data_slice)
                elif val_buf is not None:
                    val_buf.extend(data_slice)

                del buf[:d_idx + len(delim)]

                # Check next characters: could be '--' (end) or '\r\n' (next part)
                while len(buf) < 2 and bytes_left > 0:
                    buf.extend(read_more())

                if buf.startswith(b"--"):
                    if out_f:
                        out_f.close()
                    if not is_file and part_name:
                        fields[part_name] = bytes(val_buf).decode("utf-8", errors="replace").strip()
                    return fields, saved_file_path, saved_file_name, file_bytes_written
                elif buf.startswith(b"\r\n"):
                    del buf[:2]

                break
            else:
                # Delimiter not found in buffer yet: flush safe bytes to disk
                if len(buf) > carry_len:
                    write_size = len(buf) - carry_len
                    data_slice = buf[:write_size]
                    if is_file and out_f:
                        out_f.write(data_slice)
                        file_bytes_written += len(data_slice)
                    elif val_buf is not None:
                        val_buf.extend(data_slice)
                    del buf[:write_size]

                chunk = read_more()
                if not chunk:
                    # Stream exhausted
                    if is_file and out_f:
                        out_f.write(buf)
                        file_bytes_written += len(buf)
                        buf.clear()
                    elif val_buf is not None:
                        val_buf.extend(buf)
                        buf.clear()
                    break
                buf.extend(chunk)

        if out_f:
            out_f.close()
            out_f = None
        if not is_file and part_name:
            fields[part_name] = bytes(val_buf).decode("utf-8", errors="replace").strip()

    return fields, saved_file_path, saved_file_name, file_bytes_written



class WhatsAppViewerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the drag & drop web interface."""

    def log_message(self, format: str, *args) -> None:
        """Custom concise logging format with resource metrics in verbose mode."""
        if SERVER_VERBOSE:
            ram = get_ram_rss_mb()
            cpu_u, _ = get_cpu_times()
            print(f"[{self.log_date_time_string()}] {self.command} {self.path} - {args[1]} | RAM: {ram:.1f} Mo | CPU: {cpu_u:.2f}s")
        else:
            print(f"[{self.log_date_time_string()}] {self.command} {self.path} - {args[1]}")

    def do_GET(self) -> None:
        """Route GET requests."""
        path = self.path.split("?")[0].rstrip("/")

        if path in ("", "/index.html"):
            self.send_index()
            return

        if path == "/api/progress":
            self.handle_progress_api()
            return

        if path.startswith("/view/"):
            rest = path.replace("/view/", "").strip()
            parts = rest.split("/", 1)
            session_id = parts[0]
            if len(parts) == 1:
                if session_id in SESSIONS:
                    self.send_session_view(session_id)
                    return
                # Resilient fallback: relative media requested under /view/<filename>
                if len(SESSIONS) == 1:
                    fallback_id = next(iter(SESSIONS.keys()))
                    self.send_session_media(fallback_id, unquote(session_id))
                    return
                self.send_error(404, "Session introuvable ou expirée")
                return
            else:
                # Relative media requested under /view/<session_id>/<filename>
                filename = parts[1]
                self.send_session_media(session_id, unquote(filename))
                return

        if path.startswith("/download/"):
            session_id = path.replace("/download/", "").strip()
            self.send_session_download(session_id)
            return

        if path.startswith("/media/"):
            parts = path.replace("/media/", "").split("/", 1)
            if len(parts) == 2:
                session_id, filename = parts
                self.send_session_media(session_id, unquote(filename))
                return

        self.send_error(404, "Page non trouvée")

    def do_POST(self) -> None:
        """Route POST requests."""
        path = self.path.split("?")[0].rstrip("/")
        if path == "/api/convert":
            self.handle_convert_api()
            return

        self.send_error(404, "Endpoint introuvable")

    def handle_progress_api(self) -> None:
        """Return real-time decompression and conversion progress."""
        qs = parse_qs(urlparse(self.path).query)
        task_id = qs.get("task_id", [""])[0]

        with PROGRESS_LOCK:
            data = PROGRESS_TASKS.get(task_id)
            if data:
                payload = dict(data)
            else:
                payload = {
                    "phase": "waiting",
                    "percent": 0,
                    "ram_rss_mb": round(get_ram_rss_mb(), 1),
                    "cpu_user_s": round(get_cpu_times()[0], 2),
                }
        self.send_json(payload)

    def send_index(self) -> None:
        """Serve the Drag & Drop web interface."""
        try:
            content = load_template_file("server_index.html").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Erreur serveur : {e}")

    def send_session_view(self, session_id: str) -> None:
        """Serve the generated HTML chat for the session."""
        session = SESSIONS.get(session_id)
        if not session or not os.path.isfile(session["html_path"]):
            self.send_error(404, "Session introuvable ou expirée")
            return

        file_size = os.path.getsize(session["html_path"])
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        try:
            with open(session["html_path"], "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=64 * 1024)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_session_download(self, session_id: str) -> None:
        """Serve the generated HTML chat as an attachment for downloading."""
        session = SESSIONS.get(session_id)
        if not session or not os.path.isfile(session["html_path"]):
            self.send_error(404, "Session introuvable ou expirée")
            return

        file_size = os.path.getsize(session["html_path"])
        filename = "discussion_whatsapp.html"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        try:
            with open(session["html_path"], "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=64 * 1024)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_session_media(self, session_id: str, filename: str) -> None:
        """Serve a media file associated with a session with Range support for audio/video."""
        session = SESSIONS.get(session_id)
        if not session or not os.path.isdir(session["media_dir"]):
            self.send_error(404, "Fichier média introuvable")
            return

        media_root = os.path.abspath(session["media_dir"])
        clean_filename = unquote(filename).lstrip("/")
        target_path = os.path.abspath(os.path.join(media_root, clean_filename))

        # Security check: directory traversal
        try:
            if os.path.commonpath([media_root, target_path]) != media_root:
                self.send_error(403, "Accès refusé")
                return
        except ValueError:
            self.send_error(403, "Accès refusé")
            return

        if not os.path.isfile(target_path):
            self.send_error(404, "Média non trouvé")
            return

        _, ext = os.path.splitext(target_path.lower())
        mime = MIME_MAP.get(ext, "application/octet-stream")
        file_size = os.path.getsize(target_path)

        range_hdr = self.headers.get("Range")
        if range_hdr and "=" in range_hdr:
            range_val = range_hdr.split("=", 1)[1].strip()
            start_str, _, end_str = range_val.partition("-")
            try:
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                end = min(end, file_size - 1)
                if start <= end and start < file_size:
                    length = end - start + 1
                    self.send_response(206)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(length))
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    try:
                        with open(target_path, "rb") as f:
                            f.seek(start)
                            remaining = length
                            while remaining > 0:
                                chunk = f.read(min(64 * 1024, remaining))
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                remaining -= len(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return
            except ValueError:
                pass

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        try:
            with open(target_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=64 * 1024)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def handle_convert_api(self) -> None:
        """Handle multipart upload, convert the zip export and prepare HTML."""
        tracker = PerformanceTracker("Server Convert")

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json({"success": False, "error": "Requête invalide (multipart requis)"}, status=400)
            return

        boundary = extract_boundary(content_type)
        if not boundary:
            self.send_json({"success": False, "error": "En-tête multipart incomplet (boundary manquant)"}, status=400)
            return

        content_len_hdr = self.headers.get("Content-Length")
        if not content_len_hdr or not content_len_hdr.isdigit():
            self.send_json({"success": False, "error": "Taille de requête invalide"}, status=400)
            return

        content_length = int(content_len_hdr)
        # Max upload size default 10 GiB
        max_upload_size = int(os.environ.get("MAX_UPLOAD_SIZE") or (10 * 1024 * 1024 * 1024))
        if content_length > max_upload_size:
            max_gb = max_upload_size / (1024 * 1024 * 1024)
            self.send_json({"success": False, "error": f"Fichier trop volumineux (max {max_gb:.1f} Go)"}, status=413)
            return

        # Query string task_id takes precedence if present
        qs = parse_qs(urlparse(self.path).query)
        task_id = qs.get("task_id", [""])[0] or None

        # Create session directory on physical disk (avoid tmpfs RAM exhaust)
        session_id = uuid.uuid4().hex[:12]
        base_dir = get_session_base_dir()
        session_dir = os.path.join(base_dir, f"wa_session_{session_id}")
        os.makedirs(session_dir, exist_ok=True)

        # Pre-check disk space
        try:
            free_disk = shutil.disk_usage(session_dir).free
            if free_disk < content_length * 2:
                shutil.rmtree(session_dir, ignore_errors=True)
                self.send_json({
                    "success": False,
                    "error": f"Espace disque insuffisant ({free_disk / (1024**3):.1f} Go libres)",
                }, status=507)
                return
        except OSError:
            pass

        # Initialize progress tracking
        if task_id:
            with PROGRESS_LOCK:
                PROGRESS_TASKS[task_id] = {
                    "phase": "uploading",
                    "percent": 5,
                    "ram_rss_mb": round(get_ram_rss_mb(), 1),
                    "cpu_user_s": round(get_cpu_times()[0], 2),
                }

        try:
            fields, zip_path, zip_filename, file_bytes = parse_multipart_stream(
                self.rfile,
                content_length,
                boundary,
                session_dir,
                chunk_size=1024 * 1024,
            )

            if not task_id and "task_id" in fields:
                task_id = fields["task_id"]

            if not zip_path or not os.path.isfile(zip_path) or file_bytes == 0:
                self.send_json({"success": False, "error": "Aucun fichier ZIP fourni"}, status=400)
                shutil.rmtree(session_dir, ignore_errors=True)
                return

            user_me = fields.get("me") or None
            opt_standalone = fields.get("standalone", "true").lower() == "true"
            opt_thumbs = fields.get("thumbs", "true").lower() == "true"
            raw_lang = fields.get("lang", "en").lower()
            opt_lang = "fr" if raw_lang.startswith("fr") else "en"
            opt_ultra_perf = SERVER_ULTRA_PERF or (fields.get("ultra_perf", "").lower() in ("true", "1"))

            print(f"\n=======================================================")
            print(f"📦 [CONVERT] Traitement de l'archive : '{zip_filename}' ({file_bytes / (1024 * 1024):.2f} Mo)")
            print(f"   ⚙️  Mode : Standalone={opt_standalone} | Thumbs={opt_thumbs} | Ultra-Perf={opt_ultra_perf} | Lang={opt_lang}")

            extract_dir = os.path.join(session_dir, "extracted")

            # Real-time decompression progress callback (throttled to max 4 times/sec)
            last_log_time = [0.0]

            def on_decompress_progress(pinfo: dict[str, Any]) -> None:
                now = time.perf_counter()
                is_done = pinfo.get("percent") == 100
                if not is_done and (now - last_log_time[0] < 0.25):
                    return

                last_log_time[0] = now
                ram = get_ram_rss_mb()
                cpu_u, _ = get_cpu_times()
                pinfo["ram_rss_mb"] = round(ram, 1)
                pinfo["cpu_user_s"] = round(cpu_u, 2)
                pinfo["ultra_perf"] = opt_ultra_perf
                if task_id:
                    with PROGRESS_LOCK:
                        if task_id in PROGRESS_TASKS:
                            PROGRESS_TASKS[task_id].update(pinfo)

                if SERVER_VERBOSE:
                    pct = pinfo.get("percent", 0)
                    done = pinfo.get("files_extracted", 0)
                    total = pinfo.get("total_files", 0)
                    mb_done = pinfo.get("bytes_extracted", 0) / (1024 * 1024)
                    mb_tot = pinfo.get("total_bytes", 0) / (1024 * 1024)
                    cur_file = pinfo.get("current_file", "")
                    print(f"  [DÉCOMPRESSION] {pct:3d}% ({done}/{total} fichiers, {mb_done:.1f}/{mb_tot:.1f} Mo) {cur_file[:25]} | RAM: {ram:.1f} Mo | CPU user: {cpu_u:.2f}s")

            chat_file, media_dir = extract_whatsapp_zip(
                zip_path,
                extract_dir=extract_dir,
                progress_callback=on_decompress_progress,
                ultra_perf=opt_ultra_perf,
                verbose=SERVER_VERBOSE,
            )
            step_ext = tracker.mark_step("decompression")
            print(f"  ✓ Décompression terminée en {step_ext['elapsed_s']:.2f}s | RAM: {step_ext['ram_rss_mb']:.1f} Mo | CPU user: {step_ext['cpu_user_s']:.2f}s")

            # Free disk space immediately by removing the uploaded ZIP archive before parsing/rendering
            if os.path.isfile(zip_path):
                try:
                    os.remove(zip_path)
                except OSError:
                    pass

            if task_id:
                with PROGRESS_LOCK:
                    PROGRESS_TASKS[task_id] = {
                        "phase": "parsing",
                        "percent": 80,
                        "ram_rss_mb": round(get_ram_rss_mb(), 1),
                        "cpu_user_s": round(get_cpu_times()[0], 2),
                    }

            messages = parse_chat(chat_file)
            if not messages:
                self.send_json({"success": False, "error": "Aucun message trouvé dans la discussion"}, status=400)
                shutil.rmtree(session_dir, ignore_errors=True)
                return

            step_parse = tracker.mark_step("parsing")
            print(f"  ✓ Parsing discussion : {len(messages):,} messages en {step_parse['elapsed_s']:.2f}s")

            attendees = list(dict.fromkeys(m["sender"] for m in messages))
            if not user_me:
                context_hint = f"{chat_file} {session_dir}"
                user_me = auto_detect_me(attendees, context_hint=context_hint)
            else:
                user_me = resolve_me_user(user_me, attendees)

            if opt_thumbs and media_dir:
                if task_id:
                    with PROGRESS_LOCK:
                        PROGRESS_TASKS[task_id] = {
                            "phase": "thumbnails",
                            "percent": 88,
                            "ram_rss_mb": round(get_ram_rss_mb(), 1),
                            "cpu_user_s": round(get_cpu_times()[0], 2),
                        }
                num_thumbs = generate_thumbnails(media_dir)
                step_thumbs = tracker.mark_step("thumbnails")
                print(f"  ✓ Miniatures générées : {num_thumbs} en {step_thumbs['elapsed_s']:.2f}s")

            if task_id:
                with PROGRESS_LOCK:
                    PROGRESS_TASKS[task_id] = {
                        "phase": "rendering",
                        "percent": 94,
                        "ram_rss_mb": round(get_ram_rss_mb(), 1),
                        "cpu_user_s": round(get_cpu_times()[0], 2),
                    }

            output_html_path = os.path.join(session_dir, "output.html")
            html_content = build_html(
                messages,
                media_dir,
                output_path=output_html_path,
                me_user=user_me,
                standalone=opt_standalone,
                lang=opt_lang,
                media_url_prefix=f"/media/{session_id}",
            )

            with open(output_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            html_size_mb = len(html_content.encode("utf-8")) / (1024 * 1024)
            del html_content

            step_render = tracker.mark_step("rendering")
            final_metrics = tracker.finish()

            if task_id:
                with PROGRESS_LOCK:
                    PROGRESS_TASKS[task_id] = {
                        "phase": "done",
                        "percent": 100,
                        "ram_rss_mb": round(final_metrics["ram_rss_mb"], 1),
                        "peak_ram_mb": round(final_metrics["peak_ram_mb"], 1),
                        "cpu_user_s": round(final_metrics["cpu_user_s"], 2),
                        "elapsed_s": round(final_metrics["elapsed_s"], 2),
                    }

            SESSIONS[session_id] = {
                "html_path": output_html_path,
                "media_dir": media_dir,
                "session_dir": session_dir,
                "standalone": str(opt_standalone),
            }

            print(f"-------------------------------------------------------")
            print(f"✓ [CONVERT] Succès pour '{zip_filename}' en {final_metrics['elapsed_s']:.2f}s")
            print(f"  • RAM : {final_metrics['ram_rss_mb']:.1f} Mo (Pic: {final_metrics['peak_ram_mb']:.1f} Mo)")
            print(f"  • CPU : user {final_metrics['cpu_user_s']:.2f}s | sys {final_metrics['cpu_sys_s']:.2f}s | charge {final_metrics['cpu_percent']:.1f}%")
            print(f"  • Discussion : {len(messages):,} messages ({os.path.basename(chat_file)})")
            print(f"  • Sortie : {html_size_mb:.2f} Mo (standalone={opt_standalone})")
            print(f"=======================================================\n")

            self.send_json({
                "success": True,
                "session_id": session_id,
                "messages": len(messages),
                "chat_name": os.path.basename(chat_file),
                "metrics": {
                    "elapsed_s": round(final_metrics["elapsed_s"], 2),
                    "ram_rss_mb": round(final_metrics["ram_rss_mb"], 1),
                    "peak_ram_mb": round(final_metrics["peak_ram_mb"], 1),
                    "cpu_user_s": round(final_metrics["cpu_user_s"], 2),
                    "cpu_percent": round(final_metrics["cpu_percent"], 1),
                },
            })

        except Exception as e:
            if task_id:
                with PROGRESS_LOCK:
                    PROGRESS_TASKS[task_id] = {
                        "phase": "error",
                        "percent": 0,
                        "error": str(e),
                    }
            shutil.rmtree(session_dir, ignore_errors=True)
            self.send_json({"success": False, "error": str(e)}, status=400)


    def send_json(self, data: dict, status: int = 200) -> None:
        """Send a JSON HTTP response."""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = True,
    verbose: bool = False,
    ultra_perf: bool = False,
) -> None:
    """Launch the local HTTP server."""
    global SERVER_VERBOSE, SERVER_ULTRA_PERF
    SERVER_VERBOSE = verbose
    SERVER_ULTRA_PERF = ultra_perf

    cleanup_stale_sessions()

    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, WhatsAppViewerHandler)
    url = f"http://{host}:{port}"

    print(f"\n=======================================================")
    print(f"  WhatsApp Chat Viewer — Serveur Web local")
    print(f"  ➜ Interface accessible sur : {url}")
    print(f"  • Glissez-déposez vos fichiers .zip directement dans la page")
    if verbose:
        print(f"  • Mode verbeux : ACTIF (--verbose)")
    if ultra_perf:
        print(f"  • Mode Ultra-Perf : ACTIF (--ultra-perf)")
    print(f"  • Appuyez sur Ctrl+C pour arrêter le serveur.")
    print(f"=======================================================\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur...")
    finally:
        httpd.server_close()
        # Clean up temporary sessions
        for sess in SESSIONS.values():
            shutil.rmtree(sess.get("session_dir", ""), ignore_errors=True)
        cleanup_stale_sessions()
        print("✓ Serveur arrêté proprement.")
