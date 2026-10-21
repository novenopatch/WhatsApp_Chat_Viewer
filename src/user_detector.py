"""Helper functions to detect and resolve the 'Me' participant."""

from __future__ import annotations

import os
import subprocess


def resolve_me_user(me_user: str | None, attendees: list[str]) -> str | None:
    """Find the best matching attendee name for me_user (exact, case-insensitive, or substring).

    Attempts multiple matching strategies in order:
    1. Exact match
    2. Case-insensitive match
    3. Clean prefix match (removes ~, +, @ prefixes)
    4. Substring match (user string in attendee or vice versa)

    Args:
        me_user: User-specified name to match against attendees.
        attendees: List of participant names from the chat.

    Returns:
        Best matching attendee name, or original me_user if no match found.
        Returns None if me_user is None or empty.

    Example:
        >>> attendees = ["Alice", "Bob", "+Charlie"]
        >>> resolved = resolve_me_user("alice", attendees)
        >>> print(resolved)
        "Alice"
    """
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
    """Attempt to auto-detect 'me' participant from the chat.

    Uses multiple heuristics in priority order:
    1. Pronouns ('vous', 'you', 'moi', 'me') in attendee names
    2. Path/context hint matching attendee (file path, directory name)
    3. OS username from USER/USERNAME environment variable
    4. Git config user.name from local repository

    Args:
        attendees: List of participant names from the chat.
        context_hint: Optional context string (e.g., file path) to match against.

    Returns:
        Best guess for the 'me' participant name, or None if no match found.

    Example:
        >>> attendees = ["Alice", "Bob", "Me"]
        >>> detected = auto_detect_me(attendees)
        >>> print(detected)
        "Me"
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
