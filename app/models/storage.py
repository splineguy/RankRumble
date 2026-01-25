"""
JSON file storage utilities with file locking for thread safety.
"""
import fcntl
import json
import os
import secrets
import string
from datetime import datetime


def generate_id(prefix: str = '', length: int = 12) -> str:
    """Generate a random ID string."""
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(length))
    if prefix:
        return f"{prefix}_{random_part}"
    return random_part


def ensure_directory(filepath: str) -> None:
    """Ensure the directory for a file exists."""
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_json(filepath: str, default: dict = None) -> dict:
    """
    Thread-safe JSON loading with shared lock.

    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist

    Returns:
        Loaded JSON data or default value
    """
    if default is None:
        default = {}

    if not os.path.exists(filepath):
        return default

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (json.JSONDecodeError, IOError):
        return default


def save_json(filepath: str, data: dict) -> None:
    """
    Thread-safe JSON saving with exclusive lock.

    Args:
        filepath: Path to JSON file
        data: Data to save
    """
    ensure_directory(filepath)

    with open(filepath, 'w', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat() + 'Z'
