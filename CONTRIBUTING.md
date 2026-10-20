# Contributing to WhatsApp Chat Viewer

Thank you for your interest in contributing to **WhatsApp Chat Viewer**! We welcome bug reports, feature suggestions, documentation improvements, and code contributions.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat all contributors with respect and kindness.

---

## Development Setup

The project requires **Python 3.10+** and uses standard library modules whenever possible.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/BlueTechTG/whatsapp-chat-viewer.git
   cd whatsapp-chat-viewer
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install optional dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Installs Pillow for thumbnail optimization and python-dotenv for `.env` loading)*

---

## Running Tests

All automated tests use Python's built-in `unittest` framework and run quickly with zero external services:

```bash
# Run all unit and integration tests
python3 -m unittest discover -s tests -v

# Run a specific test module
python3 -m unittest tests/test_zip_handler.py
python3 -m unittest tests/test_standalone_and_server.py
```

Ensure all tests pass before submitting a pull request.

---

## Coding Guidelines

- **Zero heavy runtime dependencies**: Keep the core lightweight. Avoid adding dependencies like Flask, Django, or external JS build tools unless strictly necessary.
- **Memory efficiency**: When processing files, media, or archives, always prefer streaming algorithms (chunks of 64 KB or 1 MB) over buffering entire files into memory.
- **Type Annotations**: Use Python 3.10+ type hints (`from __future__ import annotations`, `list[dict]`, `str | None`).
- **Security-first**: Maintain directory traversal guards, HTML escaping, and quota limits.
- **Bilingual support**: When modifying UI strings, keep French and English translations in sync in [`src/i18n.py`](src/i18n.py).

---

## Git & Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

* `feat(...)`: A new feature
* `fix(...)`: A bug fix
* `perf(...)`: Performance improvement
* `refactor(...)`: Code change that neither fixes a bug nor adds a feature
* `test(...)`: Adding or updating tests
* `docs(...)`: Documentation only changes
* `chore(...)`: Maintenance tasks or build scripts

Example:
```bash
git commit -m "fix(server): stream multipart uploads directly to disk"
```

---

## Submitting a Pull Request

1. Create a feature branch from `dev` (or `main`):
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Commit your changes with clear messages.
3. Run the test suite: `python3 -m unittest discover -s tests`.
4. Push your branch to your fork and open a Pull Request targeting `dev`.
5. Fill in the Pull Request template describing the changes made and tests performed.
