# Security Policy

## Supported Versions

We provide security updates and patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.4.x   | :white_check_mark: |
| < 1.4.0 | :x:                |

---

## Security Architecture & Defenses

WhatsApp Chat Viewer handles untrusted user-supplied ZIP archives and text exports. Multiple military-grade security layers are implemented natively without relying on heavy external libraries:

1. **Anti-Zip Slip (Path Traversal Protection)**:
   - All extracted files and subdirectories are strictly verified to reside within the intended destination directory using `os.path.commonpath`.
   - Rejects relative segments (`..`), drive colons (`:`), symbolic links, hard links, and embedded null bytes (`\0`).
   - Rejects Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).

2. **Anti-Zip Bomb & Decompression DoS**:
   - **File count ceiling**: Rejects archives exceeding 50,000 files (`MAX_ZIP_FILES`).
   - **Declared size guard**: Rejects archives declaring > 10 GiB uncompressed size (`MAX_UNCOMPRESSED_SIZE`).
   - **Anti-non-recursive bomb**: Detects and rejects duplicate local header offsets.
   - **Global & per-member ratio limits**: Protects against extreme compression ratios (> 100:1).
   - **Pre-flight disk space verification**: Ensures physical disk space is available before extraction begins.
   - **Real-time streaming guards**: Immediately halts decompression and purges partial files if streamed bytes exceed quotas.

3. **Memory Safety & Streaming Uploads**:
   - Uploaded archives are streamed in chunks directly to physical disk storage, eliminating large in-memory buffers.
   - HTTP Range requests (`Accept-Ranges: bytes` / HTTP 206) stream media files directly from disk without loading full videos/audios in RAM.
   - Session directories are created on physical disk storage instead of in-memory `tmpfs` mounts.
   - Base64 caches are automatically cleared and garbage-collected upon HTML generation.

4. **HTML Sanitization & XSS Defense**:
   - All chat content, participant names, and filenames are HTML-escaped before insertion into the DOM.
   - Search indexing runs with text-only nodes to prevent script execution.

---

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please **do not** open a public issue.

Instead, please send a report privately to:
* **Email**: novenosexta77@gmail.com

Please include:
- A description of the vulnerability and its potential impact.
- Steps to reproduce or a Proof of Concept (PoC) archive.
- Any suggested fixes.

You will receive an initial response within **48 hours**, and we will work with you to patch and disclose the issue responsibly.
