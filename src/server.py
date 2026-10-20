"""Lightweight local web server with drag & drop conversion interface."""

from __future__ import annotations

import base64
import email
from email.parser import BytesParser
from email.policy import default
import http.server
import json
import os
import shutil
import tempfile
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse
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
            session_id = path.replace("/view/", "").strip()
            self.send_session_view(session_id)
            return

        if path.startswith("/download/"):
            session_id = path.replace("/download/", "").strip()
            self.send_session_download(session_id)
            return

        if path.startswith("/media/"):
            parts = path.replace("/media/", "").split("/", 1)
            if len(parts) == 2:
                session_id, filename = parts
                self.send_session_media(session_id, filename)
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

        with open(session["html_path"], "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_session_download(self, session_id: str) -> None:
        """Serve the generated HTML chat as an attachment for downloading."""
        session = SESSIONS.get(session_id)
        if not session or not os.path.isfile(session["html_path"]):
            self.send_error(404, "Session introuvable ou expirée")
            return

        with open(session["html_path"], "rb") as f:
            content = f.read()

        filename = "discussion_whatsapp.html"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_session_media(self, session_id: str, filename: str) -> None:
        """Serve a media file associated with a session."""
        session = SESSIONS.get(session_id)
        if not session or not os.path.isdir(session["media_dir"]):
            self.send_error(404, "Fichier média introuvable")
            return

        media_root = os.path.abspath(session["media_dir"])
        target_path = os.path.abspath(os.path.join(media_root, filename))

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

        with open(target_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_convert_api(self) -> None:
        """Handle multipart upload, convert the zip export and prepare HTML."""
        tracker = PerformanceTracker("Server Convert")

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json({"success": False, "error": "Requête invalide (multipart requis)"}, status=400)
            return

        content_len_hdr = self.headers.get("Content-Length")
        if not content_len_hdr or not content_len_hdr.isdigit():
            self.send_json({"success": False, "error": "Taille de requête invalide"}, status=400)
            return

        content_length = int(content_len_hdr)
        # 2 GiB upload safety limit
        if content_length > 2 * 1024 * 1024 * 1024:
            self.send_json({"success": False, "error": "Fichier trop volumineux (max 2 Go)"}, status=413)
            return

        raw_body = self.rfile.read(content_length)
        raw_headers = f"Content-Type: {content_type}\r\n\r\n".encode("latin1")

        try:
            msg = BytesParser(policy=default).parsebytes(raw_headers + raw_body)
        except Exception as e:
            self.send_json({"success": False, "error": f"Erreur de décodage multipart : {e}"}, status=400)
            return

        zip_bytes: bytes | None = None
        zip_filename = "export.zip"
        user_me: str | None = None
        opt_standalone = True
        opt_thumbs = True
        opt_lang = "en"
        task_id: str | None = None
        opt_ultra_perf = SERVER_ULTRA_PERF

        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if name == "zip_file":
                zip_bytes = part.get_payload(decode=True)
                fn = part.get_filename()
                if fn:
                    zip_filename = fn
            elif name == "me":
                val = part.get_payload(decode=True)
                if val:
                    user_me = val.decode("utf-8", errors="replace").strip() or None
            elif name == "lang":
                val = part.get_payload(decode=True)
                if val:
                    raw = val.decode("utf-8", errors="replace").strip().lower()
                    opt_lang = "fr" if raw.startswith("fr") else "en"
            elif name == "standalone":
                val = part.get_payload(decode=True)
                if val:
                    opt_standalone = val.decode("utf-8", errors="replace").strip().lower() == "true"
            elif name == "thumbs":
                val = part.get_payload(decode=True)
                if val:
                    opt_thumbs = val.decode("utf-8", errors="replace").strip().lower() == "true"
            elif name == "ultra_perf":
                val = part.get_payload(decode=True)
                if val:
                    opt_ultra_perf = val.decode("utf-8", errors="replace").strip().lower() in ("true", "1")
            elif name == "task_id":
                val = part.get_payload(decode=True)
                if val:
                    task_id = val.decode("utf-8", errors="replace").strip() or None

        if not zip_bytes:
            self.send_json({"success": False, "error": "Aucun fichier ZIP fourni"}, status=400)
            return

        # Initialize progress tracking
        if task_id:
            with PROGRESS_LOCK:
                PROGRESS_TASKS[task_id] = {
                    "phase": "starting",
                    "percent": 0,
                    "ram_rss_mb": round(get_ram_rss_mb(), 1),
                    "cpu_user_s": round(get_cpu_times()[0], 2),
                }

        # Create session directory
        session_id = uuid.uuid4().hex[:12]
        session_dir = tempfile.mkdtemp(prefix=f"wa_session_{session_id}_")

        print(f"\n=======================================================")
        print(f"📦 [CONVERT] Traitement de l'archive : '{zip_filename}' ({len(zip_bytes) / (1024 * 1024):.2f} Mo)")
        print(f"   ⚙️  Mode : Standalone={opt_standalone} | Thumbs={opt_thumbs} | Ultra-Perf={opt_ultra_perf} | Lang={opt_lang}")

        try:
            zip_path = os.path.join(session_dir, zip_filename)
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            extract_dir = os.path.join(session_dir, "extracted")

            # Real-time decompression progress callback
            last_log_time = [0.0]

            def on_decompress_progress(pinfo: dict[str, Any]) -> None:
                ram = get_ram_rss_mb()
                cpu_u, _ = get_cpu_times()
                pinfo["ram_rss_mb"] = round(ram, 1)
                pinfo["cpu_user_s"] = round(cpu_u, 2)
                pinfo["ultra_perf"] = opt_ultra_perf
                if task_id:
                    with PROGRESS_LOCK:
                        if task_id in PROGRESS_TASKS:
                            PROGRESS_TASKS[task_id].update(pinfo)

                now = time.perf_counter()
                if (now - last_log_time[0] >= 0.3) or pinfo.get("percent") == 100:
                    last_log_time[0] = now
                    pct = pinfo.get("percent", 0)
                    done = pinfo.get("files_extracted", 0)
                    total = pinfo.get("total_files", 0)
                    mb_done = pinfo.get("bytes_extracted", 0) / (1024 * 1024)
                    mb_tot = pinfo.get("total_bytes", 0) / (1024 * 1024)
                    cur_file = pinfo.get("current_file", "")
                    if SERVER_VERBOSE:
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
            )

            with open(output_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

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
            print(f"  • Sortie : {len(html_content.encode('utf-8')) / (1024 * 1024):.2f} Mo (standalone={opt_standalone})")
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
        print("✓ Serveur arrêté proprement.")
