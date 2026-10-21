# Contributing to WhatsApp Chat Viewer

Thank you for your interest in contributing to **WhatsApp Chat Viewer**! We welcome bug reports, feature suggestions, documentation improvements, and code contributions.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Style & Formatting](#code-style--formatting)
- [Testing](#testing)
- [Linting & Type Checking](#linting--type-checking)
- [Debugging](#debugging)
- [Profiling](#profiling)
- [Security Features](#security-features)
- [Coding Guidelines](#coding-guidelines)
- [Git & Commit Conventions](#git--commit-conventions)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat all contributors with respect and kindness.

---

## Development Setup

The project requires **Python 3.10+** and uses standard library modules whenever possible.

### 1. Clone the repository

```bash
git clone https://github.com/BlueTechTG/whatsapp-chat-viewer.git
cd whatsapp-chat-viewer
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

#### Production dependencies only:
```bash
pip install -r requirements.txt
```

#### With development tools (recommended for contributors):
```bash
pip install -e ".[dev]"
```

This installs:
- **Testing**: pytest, pytest-cov
- **Formatting**: black, isort
- **Linting**: ruff
- **Type checking**: mypy, types-Pillow

---

## Development Workflow

### Recommended workflow for contributors:

1. **Create a feature branch**:
   ```bash
   git checkout -b feat/my-new-feature
   ```

2. **Make your changes** following the [Coding Guidelines](#coding-guidelines)

3. **Format your code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

4. **Run linting**:
   ```bash
   ruff check src/ tests/
   ```

5. **Run type checking**:
   ```bash
   mypy src/
   ```

6. **Run tests**:
   ```bash
   python3 -m unittest discover -s tests -v
   # Or with pytest:
   pytest tests/ -v
   ```

7. **Run coverage** (optional):
   ```bash
   pytest tests/ --cov=src --cov-report=html
   # Open htmlcov/index.html in browser
   ```

8. **Commit changes** following [Git Conventions](#git--commit-conventions)

9. **Push and create PR**:
   ```bash
   git push origin feat/my-new-feature
   ```

---

## Code Style & Formatting

We use automated tools to maintain consistent code style:

### Black (Code Formatter)

Black enforces a consistent code style across the project.

```bash
# Format code
black src/ tests/

# Check if code needs formatting
black --check src/ tests/
```

Configuration: See `[tool.black]` in `pyproject.toml`

### isort (Import Sorting)

isort organizes imports according to a consistent style.

```bash
# Sort imports
isort src/ tests/

# Check if imports need sorting
isort --check-only src/ tests/
```

Configuration: See `[tool.isort]` in `pyproject.toml`

### Ruff (Linter)

Ruff is a fast Python linter that catches common errors and style issues.

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix fixable issues
ruff check --fix src/ tests/
```

Configuration: See `[tool.ruff]` in `pyproject.toml`

---

## Testing

### Running Tests

All automated tests use Python's built-in `unittest` framework:

```bash
# Run all unit and integration tests
python3 -m unittest discover -s tests -v

# Run with pytest (recommended)
pytest tests/ -v

# Run a specific test module
python3 -m unittest tests/test_zip_handler.py
pytest tests/test_zip_handler.py -v

# Run a specific test
pytest tests/test_parser.py::TestParser::test_parse_date -v
```

### Test Coverage

Generate coverage reports with pytest-cov:

```bash
# Generate terminal coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

Target coverage: 80% (adjustable in pyproject.toml)

### Writing Tests

When adding new features or fixing bugs, write tests that:

1. **Cover the happy path**: Normal usage scenarios
2. **Cover edge cases**: Boundary conditions, empty inputs, malformed data
3. **Cover error cases**: Invalid inputs, missing files, permission errors

Example test structure:
```python
import unittest
from src.parser import parse_date

class TestParser(unittest.TestCase):
    def test_parse_date_valid(self):
        """Test parsing valid date strings."""
        dt = parse_date("20/10/24 14:30:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)

    def test_parse_date_invalid(self):
        """Test parsing invalid date strings."""
        dt = parse_date("invalid date")
        self.assertIsNone(dt)
```

---

## Linting & Type Checking

### Ruff (Linting)

```bash
# Check for linting issues
ruff check src/ tests/

# Auto-fix fixable issues
ruff check --fix src/ tests/
```

### mypy (Type Checking)

mypy performs static type checking to catch type errors before runtime.

```bash
# Type check the codebase
mypy src/

# Type check with stricter rules
mypy src/ --strict
```

Configuration: See `[tool.mypy]` in `pyproject.toml`

---

## Debugging

### Using Python Debugger

Add breakpoints in your code:

```python
import pdb; pdb.set_trace()  # Python 3.6 and below
breakpoint()  # Python 3.7+
```

### Logging

The project uses structured logging (see [Logging](#logging)):

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Debug Mode

Run the CLI with verbose flag for detailed output:

```bash
python3 build.py --verbose my_export.zip
```

---

## Profiling

### CPU Profiling with cProfile

Profile the build process to identify performance bottlenecks:

```bash
python3 -m cProfile -o profile.stats build.py my_export.zip
python3 -m pstats profile.stats
# In pstats: sort cumtime, stats 20
```

### Memory Profiling

Install memory-profiler and add decorators:

```bash
pip install memory-profiler
```

```python
from memory_profiler import profile

@profile
def process_chat(file_path: str) -> list[dict]:
    # Your code here
    pass
```

Run with:
```bash
python3 -m memory_profiler build.py my_export.zip
```

---

## Security Features

### SHA-256 Hash Verification

The project includes SHA-256 hash verification for extracted files to ensure data integrity and detect corruption or tampering.

#### Using Hash Verification

Enable hash verification via CLI flag:

```bash
python3 build.py --verify-hashes my_export.zip
```

When enabled, the tool:
1. Computes SHA-256 hashes for all extracted files during ZIP extraction
2. Stores hashes in a `HashRegistry` instance
3. Verifies all files after extraction to ensure integrity
4. Reports any verification failures with detailed warnings

#### Programmatic Usage

```python
from src.hash_validator import HashRegistry, compute_sha256, verify_file_hash

# Compute a file's hash
hash_value = compute_sha256("chat.txt")

# Verify against expected hash
is_valid = verify_file_hash("chat.txt", "a1b2c3d4...")

# Use registry for batch operations
registry = HashRegistry()
registry.register("chat.txt")  # Auto-computes hash
registry.register("photo.jpg", "expected_hash")  # Or provide pre-computed

# Verify all registered files
results = registry.verify_all()

# Export/Import hash lists
registry.export_to_file("hashes.txt")
imported = HashRegistry.import_from_file("hashes.txt")
```

#### Implementation Details

- **Chunked Reading**: Hash computation uses 8 KiB chunks by default to handle large files efficiently
- **Case-Insensitive Comparison**: Hash verification is case-insensitive (hex strings)
- **Graceful Errors**: Hash computation failures are logged but don't halt extraction
- **Registry Pattern**: `HashRegistry` class provides batch operations for tracking multiple files

See [`src/hash_validator.py`](src/hash_validator.py) for full API documentation.

---

## Coding Guidelines

### Core Principles

- **Zero heavy runtime dependencies**: Keep the core lightweight. Avoid adding dependencies like Flask, Django, or external JS build tools unless strictly necessary.
- **Memory efficiency**: When processing files, media, or archives, always prefer streaming algorithms (chunks of 64 KB or 1 MB) over buffering entire files into memory.
- **Type Annotations**: Use Python 3.10+ type hints (`from __future__ import annotations`, `list[dict]`, `str | None`).
- **Security-first**: Maintain directory traversal guards, HTML escaping, quota limits, and integrity verification.
- **Bilingual support**: When modifying UI strings, keep French and English translations in sync in [`src/i18n.py`](src/i18n.py).

### Code Organization

- **Modules**: Keep modules focused on a single responsibility
- **Functions**: Functions should be small, readable, and do one thing well
- **Docstrings**: Use Google-style docstrings with Args, Returns, and Examples
- **Type hints**: All public functions should have complete type hints

### Example Code Style

```python
"""Module docstring."""

from __future__ import annotations

def process_data(input_data: str) -> dict[str, int]:
    """Process input data and return statistics.

    Args:
        input_data: Raw input string to process.

    Returns:
        Dictionary with count and length statistics.

    Example:
        >>> result = process_data("hello")
        >>> print(result)
        {'count': 5, 'words': 1}
    """
    words = input_data.split()
    return {"count": len(input_data), "words": len(words)}
```

---

## Git & Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Commit Types

- `feat(...)`: A new feature
- `fix(...)`: A bug fix
- `perf(...)`: Performance improvement
- `refactor(...)`: Code change that neither fixes a bug nor adds a feature
- `test(...)`: Adding or updating tests
- `docs(...)`: Documentation only changes
- `chore(...)`: Maintenance tasks or build scripts
- `style(...)`: Code style changes (formatting, etc.)

### Commit Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Examples

```bash
git commit -m "feat(server): add HTTP Range request support for video scrubbing"

git commit -m "fix(parser): handle malformed WhatsApp date strings gracefully"

git commit -m "perf(zip): increase chunk size to 1 MiB in ultra-perf mode"

git commit -m "docs(readme): update installation instructions for Python 3.12"
```

---

## Pull Request Process

### Before Submitting

1. **Run all checks**:
   ```bash
   black --check src/ tests/
   isort --check-only src/ tests/
   ruff check src/ tests/
   mypy src/
   pytest tests/ -v
   ```

2. **Update documentation** if needed:
   - README.md
   - CONTRIBUTING.md
   - Docstrings
   - i18n.py (for UI strings)

3. **Add tests** for new features or bug fixes

### Creating the PR

1. Push your branch:
   ```bash
   git push origin feat/my-new-feature
   ```

2. Open a Pull Request targeting `dev` (or `main` if no dev branch)

3. Fill in the PR template:
   - **Summary**: Brief description of changes
   - **Test plan**: Checklist of tests performed
   - **Breaking changes**: List any breaking changes
   - **Related issues**: Link to related GitHub issues

### Review Process

1. **Automated checks**: CI will run tests, linting, and type checking
2. **Code review**: Maintainers will review your code
3. **Feedback**: Address review comments in follow-up commits
4. **Approval**: Once approved, your PR will be merged

### After Merge

- Delete your feature branch
- Celebrate your contribution! 🎉

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions or discuss ideas
- **Documentation**: Check README.md and inline docstrings

Thank you for contributing to WhatsApp Chat Viewer! 🙏
