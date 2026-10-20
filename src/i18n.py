"""Internationalisation (i18n) support for WhatsApp Chat Viewer.

Primary language: English (en).
Supported languages: en, fr.

Usage::

    from src.i18n import get_translations
    t = get_translations("fr")
    print(t["search_placeholder"])  # → "Rechercher…"
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Translation catalogue
# ---------------------------------------------------------------------------
# Each entry is a dict keyed by BCP-47 language tag.
# Add a new language by inserting its tag alongside "en" and "fr".

_CATALOGUE: dict[str, dict[str, str]] = {
    # ---- Day names (Monday … Sunday) ----
    "day_monday":    {"en": "Monday",    "fr": "Lundi"},
    "day_tuesday":   {"en": "Tuesday",   "fr": "Mardi"},
    "day_wednesday": {"en": "Wednesday", "fr": "Mercredi"},
    "day_thursday":  {"en": "Thursday",  "fr": "Jeudi"},
    "day_friday":    {"en": "Friday",    "fr": "Vendredi"},
    "day_saturday":  {"en": "Saturday",  "fr": "Samedi"},
    "day_sunday":    {"en": "Sunday",    "fr": "Dimanche"},

    # ---- Month names (1–12) ----
    "month_1":  {"en": "January",   "fr": "janvier"},
    "month_2":  {"en": "February",  "fr": "février"},
    "month_3":  {"en": "March",     "fr": "mars"},
    "month_4":  {"en": "April",     "fr": "avril"},
    "month_5":  {"en": "May",       "fr": "mai"},
    "month_6":  {"en": "June",      "fr": "juin"},
    "month_7":  {"en": "July",      "fr": "juillet"},
    "month_8":  {"en": "August",    "fr": "août"},
    "month_9":  {"en": "September", "fr": "septembre"},
    "month_10": {"en": "October",   "fr": "octobre"},
    "month_11": {"en": "November",  "fr": "novembre"},
    "month_12": {"en": "December",  "fr": "décembre"},

    # ---- Media type labels ----
    "media_audio":    {"en": "🎤 Audio",    "fr": "🎤 Audio"},
    "media_photo":    {"en": "📷 Photo",    "fr": "📷 Photo"},
    "media_video":    {"en": "🎬 Video",    "fr": "🎬 Vidéo"},
    "media_sticker":  {"en": "🎭 Sticker",  "fr": "🎭 Sticker"},
    "media_gif":      {"en": "🎞️ GIF",      "fr": "🎞️ GIF"},
    "media_document": {"en": "📄 Document", "fr": "📄 Document"},
    "media_other":    {"en": "📎 Other",    "fr": "📎 Autre"},

    # ---- System message keywords (used for icon lookup) ----
    "sys_voice_call":   {"en": "voice call",   "fr": "appel vocal"},
    "sys_video_call":   {"en": "video call",   "fr": "appel vidéo"},
    "sys_group_call":   {"en": "group call",   "fr": "appel de groupe"},
    "sys_encrypted":    {"en": "encrypt",      "fr": "chiffr"},
    "sys_audio_omit":   {"en": "audio omit",   "fr": "audio omis"},
    "sys_deleted":      {"en": "deleted",      "fr": "supprimé"},
    "sys_muted":        {"en": "muted",        "fr": "silencieux"},
    "sys_call_back":    {"en": "call back",    "fr": "rappeler"},
    "sys_replied":      {"en": "replied",      "fr": "répondu"},

    # ---- Renderer / bubble labels ----
    "edited_badge":        {"en": "edited",         "fr": "modifié"},
    "read_status_title":   {"en": "Read",            "fr": "Lu"},
    "react_btn_title":     {"en": "React",           "fr": "Réagir"},
    "react_btn_aria":      {"en": "React to message","fr": "Réagir au message"},
    "no_message":          {"en": "No messages.",    "fr": "Aucun message."},
    "group_chat_label":    {"en": "WhatsApp Group Conversation",  "fr": "Conversation de groupe WhatsApp"},
    "chat_label":          {"en": "WhatsApp Conversation",        "fr": "Conversation WhatsApp"},
    "no_sender_option":    {"en": "-- None (All left) --",        "fr": "-- Aucun (Tous à gauche) --"},
    "me_selector_label":   {"en": "\"Me\" bubble (right):",       "fr": "Bulle \"Moi\" (droite) :"},
    "click_to_set_me":     {"en": "Click to display as 'Me'",     "fr": "Cliquer pour afficher en tant que 'Moi'"},
    "video_unsupported":   {"en": "Video not supported.",          "fr": "Vidéo non supportée."},
    "fullscreen_btn":      {"en": "Full screen",                   "fr": "Plein écran"},
    "speed_btn_title":     {"en": "Change speed (1x, 1.5x, 2x)",  "fr": "Changer la vitesse (1x, 1.5x, 2x)"},

    # ---- Stats section ----
    "stats_title":       {"en": "📊 Conversation Statistics",  "fr": "📊 Statistiques de la conversation"},
    "stats_messages":    {"en": "💬 Messages per person",      "fr": "💬 Messages par personne"},
    "stats_hourly":      {"en": "⏰ Activity by hour",         "fr": "⏰ Activité par heure"},
    "stats_media":       {"en": "📎 Media shared",             "fr": "📎 Médias échangés"},
    "stats_general":     {"en": "📅 General info",             "fr": "📅 Infos générales"},
    "stats_no_media":    {"en": "No media",                    "fr": "Aucun média"},
    "stat_total_msgs":   {"en": "Total messages",              "fr": "Total messages"},
    "stat_duration":     {"en": "Duration",                    "fr": "Durée"},
    "stat_days":         {"en": "days",                        "fr": "jours"},
    "stat_avg_day":      {"en": "Avg. / day",                  "fr": "Moy. / jour"},
    "stat_media_count":  {"en": "Media shared",                "fr": "Médias échangés"},
    "stat_most_active":  {"en": "Most active day",             "fr": "Jour le + actif"},
    "stat_day_record":   {"en": "Day record",                  "fr": "Record du jour"},
    "stat_msgs_short":   {"en": "msgs",                        "fr": "msgs"},
    "stat_msgs_hour":    {"en": "messages",                    "fr": "messages"},

    # ---- HTML template strings ----
    "search_placeholder":    {"en": "Search…",                              "fr": "Rechercher…"},
    "search_prev_title":     {"en": "Previous result (Shift+Enter)",        "fr": "Résultat précédent (Shift+Entrée)"},
    "search_next_title":     {"en": "Next result (Enter)",                  "fr": "Résultat suivant (Entrée)"},
    "gallery_btn_title":     {"en": "Media gallery",                        "fr": "Galerie de médias"},
    "gallery_btn_aria":      {"en": "Gallery",                              "fr": "Galerie"},
    "wallpaper_btn_title":   {"en": "Toggle WhatsApp wallpaper",            "fr": "Activer/désactiver le fond d'écran WhatsApp"},
    "wallpaper_btn_aria":    {"en": "Wallpaper",                            "fr": "Fond d'écran"},
    "print_btn_title":       {"en": "Print or save as PDF (Ctrl+P)",        "fr": "Imprimer ou enregistrer en PDF (Ctrl+P)"},
    "print_btn_aria":        {"en": "Print / Export PDF",                   "fr": "Imprimer / Exporter PDF"},
    "theme_btn_title":       {"en": "Toggle Dark / Light theme",            "fr": "Basculer le thème Sombre / Clair"},
    "theme_btn_aria":        {"en": "Toggle theme",                         "fr": "Basculer le thème"},
    "date_from":             {"en": "From",                                  "fr": "Du"},
    "date_to":               {"en": "to",                                    "fr": "au"},
    "filter_all_participants": {"en": "All participants",                   "fr": "Tous les participants"},
    "filter_all_months":     {"en": "All months",                           "fr": "Tous les mois"},
    "filter_media_btn":      {"en": "Media",                                "fr": "Médias"},
    "filter_media_title":    {"en": "Show only messages with media",        "fr": "Afficher uniquement les messages avec médias"},
    "filter_photos_btn":     {"en": "Photos",                               "fr": "Photos"},
    "filter_photos_title":   {"en": "Photos and Stickers",                  "fr": "Photos et Stickers"},
    "filter_videos_btn":     {"en": "Videos",                               "fr": "Vidéos"},
    "filter_audios_btn":     {"en": "Audios",                               "fr": "Audios"},
    "filter_audios_title":   {"en": "Voice notes",                          "fr": "Notes vocales"},
    "filter_docs_btn":       {"en": "Docs",                                 "fr": "Docs"},
    "filter_docs_title":     {"en": "PDF documents and files",              "fr": "Documents PDF et fichiers"},
    "filter_links_btn":      {"en": "Links",                                "fr": "Liens"},
    "filter_links_title":    {"en": "Shared links",                         "fr": "Liens partagés"},
    "filter_date_start":     {"en": "Start date",                           "fr": "Date de début"},
    "filter_date_end":       {"en": "End date",                             "fr": "Date de fin"},
    "filter_reset_btn":      {"en": "Reset",                                "fr": "Réinitialiser"},
    "filter_reset_title":    {"en": "Reset filters",                        "fr": "Réinitialiser les filtres"},
    "timeline_title":        {"en": "Quick date navigation",                "fr": "Navigation rapide par date"},
    "gallery_modal_label":   {"en": "Media gallery",                        "fr": "Galerie de médias"},
    "gallery_title":         {"en": "Media Gallery",                        "fr": "Galerie de médias"},
    "gallery_close":         {"en": "Close",                                "fr": "Fermer"},
    "gallery_tab_photos":    {"en": "Photos & Videos",                      "fr": "Photos & Vidéos"},
    "gallery_tab_audios":    {"en": "Voice notes",                          "fr": "Notes vocales"},
    "gallery_tab_docs":      {"en": "Docs & Links",                         "fr": "Docs & Liens"},
    "lb_close_title":        {"en": "Close (Esc)",                          "fr": "Fermer (Échap)"},
    "lb_prev_title":         {"en": "Previous (←)",                         "fr": "Précédent (←)"},
    "lb_next_title":         {"en": "Next (→)",                             "fr": "Suivant (→)"},
    "lb_img_alt":            {"en": "Enlarged image",                       "fr": "Image agrandie"},
    "lb_zoom_out":           {"en": "Zoom out (-)",                         "fr": "Dézoomer (-)"},
    "lb_zoom_in":            {"en": "Zoom in (+)",                          "fr": "Zoomer (+)"},
    "lb_zoom_reset":         {"en": "Fit to screen",                        "fr": "Ajuster à l'écran"},
    "lb_actual_size":        {"en": "Actual HD size (1:1)",                 "fr": "Taille réelle HD (1:1)"},
    "lb_open_hd":            {"en": "Open original HD in new tab",          "fr": "Ouvrir le fichier original HD dans un nouvel onglet"},
    "lb_fullscreen":         {"en": "Full screen (F)",                      "fr": "Plein écran (F)"},
    "reaction_picker_label": {"en": "Choose a reaction",                    "fr": "Choisir une réaction"},
    "reaction_thumb":        {"en": "Thumbs up",                            "fr": "Pouce en l'air"},
    "reaction_heart":        {"en": "Heart",                                "fr": "Cœur"},
    "reaction_laugh":        {"en": "Laughter",                             "fr": "Rires"},
    "reaction_surprised":    {"en": "Surprised",                            "fr": "Surpris"},
    "reaction_sad":          {"en": "Sad",                                  "fr": "Triste"},
    "reaction_pray":         {"en": "Thanks / Prayer",                      "fr": "Merci / Prière"},
    "scroll_top":            {"en": "Back to top",                          "fr": "Haut de page"},
    "scroll_bottom":         {"en": "Go to bottom",                         "fr": "Bas de page"},

    # ---- JavaScript runtime strings (injected via window.I18N) ----
    "js_no_results":         {"en": "No results",            "fr": "Aucun résultat"},
    "js_jump_to_msg":        {"en": "Go to message",         "fr": "Aller au message"},
    "js_jump_to_msg_arrow":  {"en": "Go to message ➔",       "fr": "Aller au message ➔"},
    "js_to_light":           {"en": "Switch to light mode",  "fr": "Passer au mode clair"},
    "js_to_dark":            {"en": "Switch to dark mode",   "fr": "Passer au mode sombre"},
    "js_filter_summary":     {"en": "messages",              "fr": "messages"},
    "js_locale":             {"en": "en-GB",                 "fr": "fr-FR"},
}

# Supported languages (order matters: first = default fallback)
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "fr")
DEFAULT_LANGUAGE = "en"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_translations(lang: str = DEFAULT_LANGUAGE) -> dict[str, str]:
    """Return a flat dict of all translation keys for *lang*.

    Falls back to English for any key not defined in *lang*.

    Args:
        lang: BCP-47 language tag (e.g. ``"en"``, ``"fr"``).

    Returns:
        Dict mapping translation key → localised string.
    """
    lang = lang.lower().split("-")[0]  # normalise "fr-FR" → "fr"
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    result: dict[str, str] = {}
    for key, variants in _CATALOGUE.items():
        result[key] = variants.get(lang) or variants.get(DEFAULT_LANGUAGE, "")
    return result


def get_day_names(lang: str = DEFAULT_LANGUAGE) -> list[str]:
    """Return localised weekday names Mon-Sun (indices 0-6)."""
    t = get_translations(lang)
    return [
        t["day_monday"],
        t["day_tuesday"],
        t["day_wednesday"],
        t["day_thursday"],
        t["day_friday"],
        t["day_saturday"],
        t["day_sunday"],
    ]


def get_month_names(lang: str = DEFAULT_LANGUAGE) -> list[str]:
    """Return localised month names (index 0 is empty, index 1-12 = Jan-Dec)."""
    t = get_translations(lang)
    return [""] + [t[f"month_{i}"] for i in range(1, 13)]


def get_system_icons(lang: str = DEFAULT_LANGUAGE) -> dict[str, str]:
    """Return the system-icon keyword → emoji map for *lang*."""
    t = get_translations(lang)
    return {
        t["sys_voice_call"]: "📞",
        t["sys_video_call"]: "📹",
        t["sys_group_call"]: "👥",
        t["sys_encrypted"]:  "🔒",
        t["sys_audio_omit"]: "🎤",
        t["sys_deleted"]:    "🗑️",
        t["sys_muted"]:      "🔕",
        t["sys_call_back"]:  "📵",
        t["sys_replied"]:    "📱",
    }


def get_media_type_map(lang: str = DEFAULT_LANGUAGE) -> dict[str, str]:
    """Return MEDIA_TYPE_MAP localised for *lang*."""
    t = get_translations(lang)
    return {
        "AUDIO":    t["media_audio"],
        "PHOTO":    t["media_photo"],
        "VIDEO":    t["media_video"],
        "STICKER":  t["media_sticker"],
        "GIF":      t["media_gif"],
        "DOCUMENT": t["media_document"],
    }
