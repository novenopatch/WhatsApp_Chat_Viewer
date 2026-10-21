# WhatsApp Chat Viewer

<div align="center">

[![CI](https://github.com/BlueTechTG/whatsapp-chat-viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/BlueTechTG/whatsapp-chat-viewer/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.4.0-brightgreen.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework: Standard Library](https://img.shields.io/badge/framework-standard_library-orange.svg)](#)

**Convert WhatsApp chat exports (`.zip` archives or `.txt` + media folders) into an interactive, modern, responsive, and blazing-fast HTML viewer.**

[English](README.md) | [Français](README.fr.md)

</div>

---

## ⚡ Highlights

* **Zero Heavy Frameworks**: Powered entirely by the Python 3 standard library and vanilla JavaScript. No Node.js, Flask, Django, or heavy bundles required.
* **Large Archive Ready**: Tested on massive exports (**1.74+ GB, 4,400+ media files**) with chunked streaming directly to disk — no RAM exhaustion or system freezes.
* **Dual Execution Modes**:
  * **Local Web Interface (`--serve`)**: Modern Drag & Drop UI with real-time decompression progress and metrics.
  * **Command-Line Interface (CLI)**: Automate conversions and CI/CD pipelines.
* **Single-File Standalone Mode**: Embed all images, stickers, and audio notes directly into a single self-contained HTML file in Base64 for easy archiving and sharing.
* **Authentic WhatsApp Web Experience**: Dark/Light modes, reply quotes with instant jump animations, reaction badges with interactive picker, audio notes with 1x/1.5x/2x speed controls, media lightbox, full gallery tab, participant analytics, and instant full-text search.
* **Publication-Ready Print & PDF Export**: Dedicated `@media print` layout with clean page breaks, document header, and page numbering.
* **Multi-Language**: Interface supports English and French (`--lang en|fr|auto`).
* **Hardened Security**: Protected against Zip Slip directory traversal, Zip bombs, and spoofed archives.

---

## 🎯 Use Cases

**WhatsApp Chat Viewer** is designed for anyone who needs to archive, analyze, or share WhatsApp conversations outside the app ecosystem:

### Personal Archiving
- **Preserve important conversations**: Relationship history, family memories, life milestones
- **Backup before account changes**: Switching phone numbers, closing accounts, or device migration
- **Long-term storage**: Keep conversations safe even if WhatsApp account is banned or lost
- **Offline access**: Read chat history without internet connection or WhatsApp Web

### Professional & Legal
- **Legal documentation**: Lawyers and paralegals preserving evidence for civil/criminal cases
- **Journalistic sources**: Interview documentation and source communication records
- **Business records**: Client discussions, project decisions, partnership agreements
- **HR documentation**: Recruitment conversations (with consent) and internal communications

### Content Creation
- **Media production**: YouTubers, streamers, and bloggers illustrating conversations
- **Storytelling**: Memoirists documenting personal and family histories
- **Social sharing**: Curated conversation excerpts for social media or presentations

### Group Moderation
- **Community archives**: Admins preserving group decisions, rules, and important discussions
- **Project documentation**: Teams maintaining conversation histories for reference
- **Event coordination**: Event planners keeping records of logistics and attendee communications

### Research & Analysis
- **Academic research**: Researchers studying digital communication patterns
- **Ethnography**: Social scientists documenting online communities
- **Data analysis**: Extracting insights from message patterns, timing, and media sharing

---

## 📊 Comparison

| Feature | WhatsApp Web | Native Export | Screenshots | WhatsApp Chat Viewer |
|---------|--------------|--------------|-------------|---------------------|
| **Offline access** | ❌ Requires internet | ✅ Yes | ✅ Yes | ✅ Yes |
| **Searchable** | ⚠️ Limited | ❌ No | ❌ No | ✅ Full-text search |
| **Visual design** | ⚠️ Mobile UI on desktop | ❌ Raw text | ✅ Visual | ✅ Modern responsive UI |
| **Media integration** | ✅ Online only | ❌ Separate folder | ❌ No | ✅ Embedded or linked |
| **Analytics/Stats** | ❌ None | ❌ None | ❌ None | ✅ Detailed dashboard |
| **Standalone file** | ❌ No | ⚠️ Text only | ❌ Images only | ✅ Single HTML file |
| **Print/PDF export** | ❌ Poor | ❌ No | ⚠️ Manual | ✅ Publication-ready |
| **Dark mode** | ✅ Yes | ❌ No | ❌ No | ✅ System + manual |
| **Security validation** | ✅ Official | ❌ None | ❌ None | ✅ Zip Slip/Bomb protection |
| **Hash verification** | ❌ No | ❌ No | ❌ No | ✅ SHA-256 integrity |
| **Cost** | Free | Free | Free | **Free & Open Source** |
| **Cross-platform** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Python 3.10+ |

---

## 🚀 Key Features

### 🎨 Faithful WhatsApp Web Interface
- **Participant Separation ("Me" vs "Others")**: Sent messages align to the right with WhatsApp green bubbles (`#d9fdd3` / `#005c4b`); received messages align to the left on clean white/dark backgrounds with colored author names.
- **Dynamic "Me" Switcher**: Change the active persona directly from the header dropdown without reloading.
- **Official Dark Mode**: Automatic system preference detection (`prefers-color-scheme: dark`) with manual toggle switch and `localStorage` persistence.
- **Voice Notes & Audio Player**: Inline speed selector (**1x**, **1.5x**, **2x**) and seek bar for `.opus`, `.ogg`, `.mp3`, `.m4a` files.
- **Quoted Messages & Replies**: Authentic quote boxes with colored accent bars. Clicking a quote smoothly scrolls directly to the original message with an attention pulse.
- **Emoji Reactions**: Automatic detection and grouping of reactions (`👍 ❤️ 😂 😮 😢 🙏`). Hover over messages to open the floating reaction picker with live local state.
- **Media Lightbox & Gallery**:
  - Full-screen viewer for photos and videos with zoom controls and keyboard navigation (`←` / `→` / `Esc`).
  - Tabbed media gallery drawer (Photos, Audios, Documents, Links).

### ⚡ Blazing Performance
- **Streaming Uploads & Range Requests**: Uploads are processed in 1 MB chunks to physical disk storage, keeping server RAM below 45 MB. Media files support `Accept-Ranges: bytes` (HTTP 206) for instant audio/video scrubbing.
- **Thumbnail Optimization (`--thumbs`)**: Parallel image scaling via ThreadPool to keep scrolling silky smooth at 60/120 fps.
- **CSS `content-visibility: auto`**: Browser rendering calculates only messages in the visible viewport.
- **Zero-DOM Worker Search**: Non-blocking client-side search with 200ms debounce and navigation keys (`Enter` / `Shift+Enter`).
- **Comprehensive Analytics**: Collapsible dashboard showing message breakdown per participant, 24-hour activity heatmaps, media counts, and busiest days.

---

## 📦 Building Standalone Executables

### Download Pre-built Executables

Pre-built executables for Windows, macOS, and Linux are available on the [GitHub Releases](https://github.com/BlueTechTG/whatsapp-chat-viewer/releases) page. Simply download the appropriate file for your platform and run it directly—no Python installation required.

### Building from Source

You can also build standalone executables yourself for Windows, macOS, and Linux.

#### Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

#### Build Instructions

**Linux / macOS:**
```bash
# Make the build script executable
chmod +x build_exe.sh

# Run the build script
./build_exe.sh
```

**Windows:**
```cmd
# Run the build script
build_exe.bat
```

**Manual build (all platforms):**
```bash
# Install dependencies
pip install -r requirements.txt

# Build single-file executable (recommended for distribution)
pyinstaller --onefile whatsapp_chat_viewer.spec
```

The executable will be created in the `dist/` directory:
- **Linux/macOS**: `dist/whatsapp-chat-viewer`
- **Windows**: `dist/whatsapp-chat-viewer.exe`

#### Usage

Run the executable like the Python script:
```bash
# Linux/macOS
./dist/whatsapp-chat-viewer my_export.zip

# Windows
dist\whatsapp-chat-viewer.exe my_export.zip

# Start the web server
./dist/whatsapp-chat-viewer --serve
```

#### Build Options

**Directory-based executable (faster startup, larger size):**
```bash
pyinstaller whatsapp_chat_viewer.spec
```

**Without UPX compression (faster build, larger size):**
```bash
pyinstaller --noupx whatsapp_chat_viewer.spec
```

**With custom icon:**
Edit `whatsapp_chat_viewer.spec` and set `icon='path/to/icon.ico'` (Windows) or `icon='path/to/icon.icns'` (macOS).

#### Automated CI/CD Builds

The project includes a GitHub Actions workflow (`.github/workflows/build-exe.yml`) that automatically builds executables for all platforms when you push a version tag:

```bash
# Tag a new version
git tag v1.5.0
git push origin v1.5.0
```

This will trigger the build workflow and create a GitHub Release with pre-built executables for:
- `whatsapp-chat-viewer-linux` (Linux executable)
- `whatsapp-chat-viewer-macos` (macOS executable)
- `whatsapp-chat-viewer-windows.exe` (Windows executable)

---

## 🏗️ Project Architecture

```text
whatsapp_chat_viewer/
├── build.py                # Main CLI entry point & CLI parser
├── whatsapp_chat_viewer.spec  # PyInstaller configuration for standalone executables
├── build_exe.sh            # Build script for Linux/macOS
├── build_exe.bat           # Build script for Windows
├── src/
│   ├── config.py           # Configuration loader (CLI args, .env, defaults, prompts)
│   ├── constants.py        # Regex patterns, media maps, avatar colors
│   ├── hash_validator.py   # SHA-256 hash verification for file integrity
│   ├── i18n.py             # Internationalization (English & French strings)
│   ├── logging_config.py   # Structured logging configuration
│   ├── monitor.py          # Process memory (RSS/Peak) and CPU performance tracking
│   ├── parser.py           # WhatsApp chat line parser, markdown, dates, reactions
│   ├── renderer.py         # HTML assembly, Base64 encoder, thumbnail generator
│   ├── server.py           # Lightweight HTTP server with streaming upload & range requests
│   ├── stats.py            # Chat statistics and analytics generator
│   ├── user_detector.py    # Automatic "Me" sender detection heuristics
│   ├── zip_handler.py      # Hardened ZIP extraction & Zip Slip/Bomb validation
│   └── templates/
│       ├── base.html       # HTML layout template
│       ├── style.css       # Responsive styling & official WhatsApp palettes
│       ├── app.js          # Client-side logic (audio player, lightbox, search, reactions)
│       └── server_index.html # Drag & Drop local web server UI
├── tests/                  # 150+ unit and integration tests
├── .env.example            # Environment configuration template
├── CONTRIBUTING.md         # Contribution guidelines
├── CODE_OF_CONDUCT.md      # Contributor Covenant Code of Conduct
├── SECURITY.md             # Security policy & vulnerability reporting
└── LICENSE                 # MIT License
```

---

## 🛠️ Quick Start

### 1. Requirements

* **Python 3.10+** (Python 3.10, 3.11, 3.12, 3.13, 3.14).
* Optional dependencies for image thumbnails and `.env` loading:
  ```bash
  pip install -r requirements.txt
  ```

---

### 2. Web Drag & Drop Mode (Recommended)

Start the local server and open the web interface:

```bash
# Start server on default port 8080
python3 build.py --serve

# With verbose resource tracking and Ultra-Performance mode:
python3 build.py --serve -v --ultra-perf
```

1. Open your browser at `http://127.0.0.1:8080`.
2. Drag and drop your WhatsApp `.zip` export.
3. Monitor real-time extraction progress and system metrics.
4. Click **View Conversation** or download the generated HTML!

---

### 3. Command-Line Interface (CLI)

```bash
# 📦 Convert directly from a WhatsApp ZIP export (iOS or Android)
python3 build.py my_export.zip

# 📄 Produce a single 100% self-contained standalone HTML file
python3 build.py my_export.zip --standalone -o standalone_chat.html

# 🎯 Specify output, your name, language, and thumbnail generation
python3 build.py --zip export.zip --output chat.html --me "Alice" --lang en --thumbs

# 📁 Convert from an already extracted folder
python3 build.py --dir /path/to/extracted_folder/

# ⚙️ Point to chat text and media directory manually
python3 build.py --chat chat.txt --media media/ --output chat.html
```

#### CLI Options Reference

| Option | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `input_target` | | Positional path to `.zip`, `.txt` file, or export directory | None |
| `--serve` | | Start the local Drag & Drop web server | `False` |
| `--port` | | Port for the web server | `8080` |
| `--host` | | Host for the web server | `127.0.0.1` |
| `--standalone` | `--embed` | Embed images, audio, and stickers in Base64 | `False` |
| `--max-embed-size` | | Max file size in MB per embedded media in standalone | `20` |
| `--zip` | `-z` | Path to WhatsApp export `.zip` file | None |
| `--extract-dir` | | Target folder for ZIP extraction | Archive name |
| `--dir` | `-d` | Path to extracted WhatsApp folder | None |
| `--chat` | `-c` | Path to `_chat.txt` or `chat.txt` file | None |
| `--media` | `-m` | Path to media directory | Alongside chat |
| `--output` | `-o` | Output HTML destination path | `output.html` |
| `--me` | `--your-name`| Your name / handle in the chat (green right-hand bubbles) | Auto-detected |
| `--lang` | `-l` | Interface language (`auto`, `en`, `fr`) | `auto` |
| `--thumbs` | | Generate optimized image thumbnails for faster initial load | `False` |
| `--verbose` | `-v` | Verbose logging with RAM RSS and CPU usage | `False` |
| `--ultra-perf` | `--fast` | Turbo decompression (1 MB chunks) and optimized encoding | `False` |

---

### 4. Configuration via `.env`

Copy [`.env.example`](.env.example) to `.env` to define defaults without passing CLI flags:

```ini
ZIP_FILE=/path/to/WhatsApp_Export.zip
OUTPUT_FILE=my_chat.html
ME="My Name"
LANG=en
MAX_UNCOMPRESSED_SIZE=10737418240
```

Run with zero arguments:
```bash
python3 build.py
```

---

## 🔒 Security Architecture

WhatsApp Chat Viewer is built with defensive defaults to safely process untrusted archives:
* **Anti-Zip Slip**: Path sanitization blocks `../` directory escapes and path traversals.
* **Symlink Prohibition**: Rejects symbolic links and device nodes embedded in archives.
* **Quota Guards**: Hard limits on file counts (`MAX_ZIP_FILES=50000`) and uncompressed size (`MAX_UNCOMPRESSED_SIZE=10GB`).
* **Streaming Guards**: Decompression enforces byte quotas on-the-fly and rolls back partial writes immediately upon violation.
* **HTML Sanitization**: All messages and participant names are escaped to prevent cross-site scripting (XSS).

See [SECURITY.md](SECURITY.md) for full details and vulnerability reporting guidelines.

---

## 🧪 Testing

The test suite covers parser heuristics, golden regression tests, security boundaries, stats calculations, and web server operations:

```bash
# Run all 150+ tests
python3 -m unittest discover -s tests -v

# Run with coverage (optional)
pip install coverage
coverage run -m unittest discover -s tests
coverage report -m
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md) before opening a pull request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Copyright (c) 2024-2026 BlueTechTG.
