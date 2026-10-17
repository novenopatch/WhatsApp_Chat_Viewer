"""Helper functions to detect and resolve the 'Me' participant."""

import os
import subprocess


def resolve_me_user(me_user: str | None, attendees: list[str]) -> str | None:
    """Find the best matching attendee name for me_user (exact, case-insensitive, or substring)."""
    if not me_user:
        return None
    cleaned = me_user.strip()
    if not cleaned:
        return None
    # 1. Exact match
    for a in attendees:
        if a == cleaned:
            return a
    # 2. Case-insensitive match
    for a in attendees:
        if a.lower() == cleaned.lower():
            return a
    # 3. Clean prefix like ~ or + or @
    cleaned_strip = cleaned.lstrip("~+@ ")
    for a in attendees:
        if a.lstrip("~+@ ").lower() == cleaned_strip.lower():
            return a
    # 4. Substring match
    for a in attendees:
        if cleaned.lower() in a.lower() or a.lower() in cleaned.lower():
            return a
    return cleaned


def auto_detect_me(attendees: list[str], context_hint: str = "") -> str | None:
    """Attempt to auto-detect 'me' participant:

    1. Pronouns ('vous', 'you', 'moi', 'me')
    2. Path/context hint matching attendee
    3. OS username / user env
    4. Git config user.name
    """
    if not attendees:
        return None

    # 1. Pronouns
    for a in attendees:
        if a.strip().lower() in ("vous", "you", "moi", "me"):
            return a

    # 2. Path context hint
    if context_hint:
        hint_lower = context_hint.lower()
        for a in attendees:
            clean_a = a.lstrip("~+@ ").lower()
            if clean_a and clean_a in hint_lower:
                return a

    # 3. OS username
    os_user = (os.environ.get("USER") or os.environ.get("USERNAME") or "").strip().lower()
    if os_user and len(os_user) >= 3:
        for a in attendees:
            if os_user in a.lower():
                return a

    # 4. Git config user.name
    try:
        git_user = subprocess.check_output(
            ["git", "config", "user.name"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip().lower()
        if git_user and len(git_user) >= 3:
            for a in attendees:
                if git_user in a.lower() or a.lower() in git_user:
                    return a
    except Exception:
        pass

    return None
