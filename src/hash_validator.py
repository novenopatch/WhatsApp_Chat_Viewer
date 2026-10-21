"""SHA-256 hash validation for file integrity verification.

Provides utilities to compute and verify SHA-256 hashes of files,
ensuring that extracted files match expected values and detecting
corruption or tampering.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from src.logging_config import get_logger

logger = get_logger(__name__)


def compute_sha256(file_path: str, chunk_size: int = 8192) -> str:
    """Compute SHA-256 hash of a file.

    Reads the file in chunks to handle large files efficiently
    without loading the entire file into memory.

    Args:
        file_path: Path to the file to hash.
        chunk_size: Size of chunks to read (default: 8 KiB).

    Returns:
        Hexadecimal SHA-256 hash string (64 characters).

    Raises:
        FileNotFoundError: If file does not exist.
        OSError: If file cannot be read.

    Example:
        >>> hash_val = compute_sha256("chat.txt")
        >>> print(hash_val)
        "a1b2c3d4e5f6..."
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def verify_file_hash(
    file_path: str,
    expected_hash: str,
    chunk_size: int = 8192,
) -> bool:
    """Verify that a file's SHA-256 hash matches the expected value.

    Args:
        file_path: Path to the file to verify.
        expected_hash: Expected SHA-256 hash (hex string).
        chunk_size: Size of chunks to read (default: 8 KiB).

    Returns:
        True if hash matches, False otherwise.

    Example:
        >>> if verify_file_hash("chat.txt", "a1b2c3..."):
        ...     print("File integrity verified")
    """
    try:
        actual_hash = compute_sha256(file_path, chunk_size)
        matches = actual_hash.lower() == expected_hash.lower()
        if not matches:
            logger.warning(
                f"Hash mismatch for {file_path}: "
                f"expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
            )
        return matches
    except (FileNotFoundError, OSError) as e:
        logger.error(f"Failed to compute hash for {file_path}: {e}")
        return False


class HashRegistry:
    """Registry for storing and verifying file hashes.

    Tracks SHA-256 hashes of extracted files to enable integrity
    verification and detect corruption or tampering.

    Attributes:
        hashes: Dictionary mapping file paths to their SHA-256 hashes.
    """

    def __init__(self) -> None:
        """Initialize an empty hash registry."""
        self.hashes: dict[str, str] = {}

    def register(self, file_path: str, hash_value: str | None = None) -> str:
        """Register a file's hash in the registry.

        If hash_value is provided, stores it directly. Otherwise,
        computes the hash from the file.

        Args:
            file_path: Path to the file.
            hash_value: Optional pre-computed hash. If None, computes hash.

        Returns:
            The SHA-256 hash (hex string).

        Raises:
            FileNotFoundError: If file does not exist and hash_value is None.
        """
        if hash_value is None:
            hash_value = compute_sha256(file_path)
        self.hashes[file_path] = hash_value
        return hash_value

    def verify(self, file_path: str) -> bool:
        """Verify a file's hash against the registered value.

        Args:
            file_path: Path to the file to verify.

        Returns:
            True if hash matches or file not registered, False if mismatch.

        Example:
            >>> registry = HashRegistry()
            >>> registry.register("chat.txt")
            >>> if registry.verify("chat.txt"):
            ...     print("File verified")
        """
        if file_path not in self.hashes:
            logger.debug(f"No hash registered for {file_path}, skipping verification")
            return True

        expected = self.hashes[file_path]
        return verify_file_hash(file_path, expected)

    def verify_all(self) -> dict[str, bool]:
        """Verify all registered files.

        Returns:
            Dictionary mapping file paths to verification results (True/False).
        """
        results = {}
        for file_path in self.hashes:
            results[file_path] = self.verify(file_path)
        return results

    def export_to_file(self, output_path: str) -> None:
        """Export the hash registry to a file.

        Each line contains: hash  filepath

        Args:
            output_path: Path to write the hash file.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for file_path, hash_value in sorted(self.hashes.items()):
                f.write(f"{hash_value}  {file_path}\n")
        logger.info(f"Hash registry exported to {output_path}")

    @classmethod
    def import_from_file(cls, input_path: str) -> HashRegistry:
        """Import a hash registry from a file.

        Expected format: hash  filepath (one per line)

        Args:
            input_path: Path to the hash file.

        Returns:
            HashRegistry instance with imported hashes.

        Raises:
            FileNotFoundError: If input file does not exist.
            ValueError: If file format is invalid.
        """
        registry = cls()
        with open(input_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)  # Split on first whitespace
                if len(parts) != 2:
                    logger.warning(f"Invalid hash format at line {line_num}: {line}")
                    continue
                hash_value, file_path = parts
                registry.hashes[file_path] = hash_value
        logger.info(f"Imported {len(registry.hashes)} hashes from {input_path}")
        return registry

    def get_report(self) -> str:
        """Generate a human-readable report of the hash registry.

        Returns:
            Formatted string with file count and hash summary.
        """
        total = len(self.hashes)
        return f"Hash Registry: {total} files tracked"
