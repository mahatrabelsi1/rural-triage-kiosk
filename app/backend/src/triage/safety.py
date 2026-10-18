"""Critical-language safety overrides.

These patterns run on the raw chief complaint and force RED regardless of the
symptom ratings. They are intentionally broad: a false RED costs a few minutes
of clinician time, a missed one can cost a life.
"""

import re

from .schemas import MatchedRule

# Straight, curly and backtick apostrophes are dropped so "I'm" / "I’m" / "Im"
# all normalize to "im" and "can't" becomes "cant".
_APOSTROPHES = re.compile(r"['’‘`´]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_I_AM = r"\bi\s*(?:am|m)?\s*"
_GOING_TO = r"(?:gonna|ganna|gunna|gona|going\s*to|goin\s*to|about\s*to)"

CRITICAL_PATTERNS: list[dict] = [
    {
        "id": "S1",
        "reason": "Critical distress language detected in chief complaint.",
        "patterns": [
            re.compile(_I_AM + _GOING_TO + r"\s*die\b"),
            re.compile(r"\bi\s*(?:am|m)\s*dying\b"),
            re.compile(r"\bi\s*(?:will|ll)\s*die\b"),
            re.compile(r"\bi\s*think\s*i\s*(?:am|m)?\s*(?:dying|going\s*to\s*die)\b"),
        ],
    },
    {
        "id": "S2",
        "reason": "Possible self-harm or suicidal language detected in chief complaint.",
        "patterns": [
            re.compile(r"\b(?:want|wanna|wish|plan|planning)\s*(?:to\s*)?(?:die|be\s*dead)\b"),
            re.compile(r"\bkill(?:ing)?\s*my\s*self\b"),
            re.compile(r"\bsuicid"),
            re.compile(r"\bend\s*(?:my\s*life|it\s*all)\b"),
            re.compile(r"\b(?:dont|do\s*not)\s*want\s*to\s*live\b"),
            re.compile(r"\bhurt(?:ing)?\s*my\s*self\b"),
        ],
    },
    {
        "id": "S3",
        "reason": "Airway or breathing emergency language detected in chief complaint.",
        "patterns": [
            re.compile(r"\b(?:cant|cannot|can\s*not|unable\s*to|could\s*not|couldnt)\s*breath(?:e|ing)?\b"),
            re.compile(r"\bnot\s*breathing\b"),
            re.compile(r"\bstopped\s*breathing\b"),
            re.compile(r"\bchoking\b"),
        ],
    },
    {
        "id": "S4",
        "reason": "Collapse, unresponsiveness, or seizure language detected in chief complaint.",
        # "no history of seizures" should not force RED, so these terms honor negation.
        "negatable": True,
        "patterns": [
            re.compile(r"\bunconscious\b"),
            re.compile(r"\bunresponsive\b"),
            re.compile(r"\bnot\s*waking\s*up\b"),
            re.compile(r"\bseizure|\bconvuls|\bfitting\b"),
        ],
    },
]


_NEGATIONS = {"no", "not", "never", "without", "denies", "denied", "deny"}


def _negated(normalized: str, start: int) -> bool:
    return any(token in _NEGATIONS for token in normalized[:start].split()[-3:])


def _category_hit(normalized: str, category: dict) -> bool:
    for pattern in category["patterns"]:
        for match in pattern.finditer(normalized):
            if not category.get("negatable") or not _negated(normalized, match.start()):
                return True
    return False


def normalize_for_safety(text: str) -> str:
    lowered = _APOSTROPHES.sub("", (text or "").lower())
    return _NON_ALNUM.sub(" ", lowered).strip()


def detect_critical_language(text: str) -> list[MatchedRule]:
    """Return one MatchedRule per critical category found in the text."""
    normalized = normalize_for_safety(text)
    if not normalized:
        return []

    hits: list[MatchedRule] = []
    for category in CRITICAL_PATTERNS:
        if _category_hit(normalized, category):
            hits.append(MatchedRule(id=category["id"], reason=category["reason"]))
    return hits
