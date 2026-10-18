import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def _load_json(path: str, mtime_ns: int) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_json_cached(path: Path) -> dict:
    """Parse a JSON file once and reuse it until the file changes on disk,
    so rules.json edits still apply without restarting the server."""
    return _load_json(str(path), path.stat().st_mtime_ns)


def load_rules(rules_path: Path) -> dict:
    if not rules_path.exists():
        raise FileNotFoundError(f"rules.json not found at: {rules_path}")
    return load_json_cached(rules_path)
