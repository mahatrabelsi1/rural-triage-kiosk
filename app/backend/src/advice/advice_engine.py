import json
from pathlib import Path
from typing import Dict, List

def load_catalog(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def green_advice(symptoms: Dict[str, int], catalog: dict) -> List[str]:
    blocks: List[str] = []
    for key, text in catalog.items():
        if int(symptoms.get(key, 0)) >= 1:
            blocks.append(text)
    # fallback generic
    if not blocks:
        blocks.append("Rest, hydrate, and monitor symptoms. Seek care if symptoms worsen or new severe symptoms appear.")
    return blocks
