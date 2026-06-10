from pathlib import Path


def get_cache_dir() -> Path:
    """Get the path to the cache directory, creating it if it doesn't exist."""
    cache_dir = Path(__file__).parent.parent / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
