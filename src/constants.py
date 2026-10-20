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

# Quotes & Reactions patterns
QUOTE_LINE_PATTERN = re.compile(r"^>\s?(.*)$")
QUOTE_AUTHOR_PATTERN = re.compile(r"^(?:\[([^\]]+)\]|([^:]+)):\s*(.*)$")

EMOJI_PATTERN = re.compile(r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b06\ufe0f\u200d]+")

REACTION_LINE_PATTERN = re.compile(
    r"^(?:(?:a réagi (?:par|avec)?\s*|reacted (?:with)?\s*)?"
    r"([\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b06\ufe0f\u200d]+)"
    r"\s*(?:à|to)\s*[\"“](.+?)[\"”]\s*)$",
    re.IGNORECASE | re.UNICODE,
)

TRAILING_REACTION_PATTERN = re.compile(
    r"\s*(?:\[(?:Reactions?|Réactions?):\s*([^\]]+)\]"
    r"|\[([\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b06\ufe0f\u200d\s,]+)\]"
    r"|\(([\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b06\ufe0f\u200d\s,]+)\))\s*$",
    re.IGNORECASE | re.UNICODE,
)

DEFAULT_REACTION_EMOJIS = ["👍", "❤️", "😂", "😮", "😢", "🙏"]

# ZIP security limits (Zip bomb / DoS protection)
DEFAULT_MAX_ZIP_FILES = 50_000
DEFAULT_MAX_UNCOMPRESSED_SIZE = 10 * 1024 * 1024 * 1024  # 10 GiB
DEFAULT_MAX_COMPRESSION_RATIO = 100.0  # Alert if ratio > 100 on files > 10 MiB
DEFAULT_MIN_RATIO_THRESHOLD = 50 * 1024 * 1024  # 50 MiB threshold before ratio guards trigger
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


