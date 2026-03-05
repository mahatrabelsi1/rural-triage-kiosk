import json
from pathlib import Path

def load_rules(rules_path: Path) -> dict:
    if not rules_path.exists():
        raise FileNotFoundError(f"rules.json not found at: {rules_path}")
    with rules_path.open("r", encoding="utf-8") as f:
        return json.load(f)
