"""Constants and regular expressions used across the WhatsApp Chat Viewer."""

import re

# Regex for WhatsApp messages, handling optional LTR mark \u200e and brackets
MESSAGE_PATTERN = re.compile(
    r"^\u200e?\[(\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}:\d{2})\] ([^:]+): (.*)$"
)

ATTACHMENT_KEYWORDS = ["pièce jointe :", "file attached:", "attached:"]

DATE_FORMATS = [
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
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

EDIT_ANNOTATION_PATTERN = re.compile(r"\s*\u200e?<Ce message a été modifié>\s*$")
DELETE_ANNOTATION_PATTERN = re.compile(r"\s*\u200e?<Ce message a été supprimé>\s*$")
URL_PATTERN = re.compile(r"(https?://[^\s<>\"']+)")

# WhatsApp markdown (applied on HTML-escaped text; *, _, ~, ` are not HTML-special)
WA_CODE_BLOCK = re.compile(r"```([\s\S]+?)```")
WA_MONO = re.compile(r"`([^`\n]+)`")
WA_BOLD = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
WA_ITALIC = re.compile(r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)")
WA_STRIKE = re.compile(r"(?<!~)~(?!\s)(.+?)(?<!\s)~(?!~)")

SYSTEM_ICONS = {
    "appel vocal": "📞", "appel vidéo": "📹", "appel de groupe": "👥",
    "chiffr": "🔒", "audio omis": "🎤", "supprimé": "🗑️",
    "silencieux": "🔕", "rappeler": "📵", "répondu": "📱",
}

MEDIA_TYPE_MAP = {
    "AUDIO": "🎤 Audio",
    "PHOTO": "📷 Photo",
    "VIDEO": "🎬 Vidéo",
    "STICKER": "🎭 Sticker",
    "GIF": "🎞️ GIF",
    "DOCUMENT": "📄 Document",
}
