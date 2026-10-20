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
import uuid
import webbrowser

from src.parser import parse_chat
from src.renderer import build_html, generate_thumbnails, load_template_file, MIME_MAP
from src.user_detector import auto_detect_me, resolve_me_user
from src.zip_handler import extract_whatsapp_zip

# Active conversion sessions: session_id -> {html_path, media_dir, tmp_dir}
SESSIONS: dict[str, dict[str, str]] = {}


class WhatsAppViewerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the drag & drop web interface."""

    def log_message(self, format: str, *args) -> None:
        """Custom concise logging format."""
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} - {args[1]}")

    def do_GET(self) -> None:
        """Route GET requests."""
        path = self.path.split("?")[0].rstrip("/")

        if path in ("", "/index.html"):
            self.send_index()
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
            elif name == "standalone":
                val = part.get_payload(decode=True)
                if val:
                    opt_standalone = val.decode("utf-8", errors="replace").strip().lower() == "true"
            elif name == "thumbs":
                val = part.get_payload(decode=True)
                if val:
                    opt_thumbs = val.decode("utf-8", errors="replace").strip().lower() == "true"

        if not zip_bytes:
            self.send_json({"success": False, "error": "Aucun fichier ZIP fourni"}, status=400)
            return

        # Create session directory
        session_id = uuid.uuid4().hex[:12]
        session_dir = tempfile.mkdtemp(prefix=f"wa_session_{session_id}_")

        try:
            zip_path = os.path.join(session_dir, zip_filename)
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            extract_dir = os.path.join(session_dir, "extracted")
            chat_file, media_dir = extract_whatsapp_zip(zip_path, extract_dir=extract_dir)

            messages = parse_chat(chat_file)
            if not messages:
                self.send_json({"success": False, "error": "Aucun message trouvé dans la discussion"}, status=400)
                return

            attendees = list(dict.fromkeys(m["sender"] for m in messages))
            if not user_me:
                context_hint = f"{chat_file} {session_dir}"
                user_me = auto_detect_me(attendees, context_hint=context_hint)
            else:
                user_me = resolve_me_user(user_me, attendees)

            if opt_thumbs and media_dir:
                generate_thumbnails(media_dir)

            output_html_path = os.path.join(session_dir, "output.html")
            html_content = build_html(
                messages,
                media_dir,
                output_path=output_html_path,
                me_user=user_me,
                standalone=opt_standalone,
            )

            with open(output_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            SESSIONS[session_id] = {
                "html_path": output_html_path,
                "media_dir": media_dir,
                "session_dir": session_dir,
                "standalone": str(opt_standalone),
            }

            self.send_json({
                "success": True,
                "session_id": session_id,
                "messages": len(messages),
                "chat_name": os.path.basename(chat_file),
            })

        except Exception as e:
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


def run_server(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True) -> None:
    """Launch the local HTTP server."""
    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, WhatsAppViewerHandler)
    url = f"http://{host}:{port}"

    print(f"\n=======================================================")
    print(f"🌐 WhatsApp Chat Viewer - Mode Serveur Web démarré")
    print(f"👉 Ouvrez votre navigateur sur : {url}")
    print(f"📦 Glissez-déposez vos fichiers .zip directement dans la page")
    print(f"🛑 Appuyez sur Ctrl+C pour arrêter le serveur.")
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
