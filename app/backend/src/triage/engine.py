from typing import Dict, List, Tuple
from .schemas import MatchedRule

def _eval_condition(symptoms: Dict[str, int], cond: dict) -> bool:
    key = cond["symptom"]
    op = cond["op"]
    value = int(cond["value"])
    x = int(symptoms.get(key, 0))

    if op == ">=":
        return x >= value
    if op == "==":
        return x == value
    if op == "<=":
        return x <= value
    if op == ">":
        return x > value
    if op == "<":
        return x < value
    raise ValueError(f"Unsupported operator: {op}")

def _match_rule(symptoms: Dict[str, int], rule: dict) -> bool:
    logic = rule["logic"]  # "ANY" or "ALL"
    checks = [_eval_condition(symptoms, c) for c in rule["conditions"]]
    return any(checks) if logic == "ANY" else all(checks)

def run_triage(symptoms: Dict[str, int], rules: dict) -> Tuple[str, List[MatchedRule]]:
    matched: List[MatchedRule] = []

    # 1) RED rules
    for rule in rules.get("red_rules", []):
        if _match_rule(symptoms, rule):
            matched.append(MatchedRule(id=rule["id"], reason=rule["reason"]))
    if matched:
        return "RED", matched

    # 2) ORANGE rules
    for rule in rules.get("orange_rules", []):
        if _match_rule(symptoms, rule):
            matched.append(MatchedRule(id=rule["id"], reason=rule["reason"]))
    if matched:
        return "ORANGE", matched

    # 3) GREEN
    return "GREEN", matched
