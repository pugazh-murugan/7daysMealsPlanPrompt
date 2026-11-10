"""Check a generated plan against the rules in the prompt."""
from __future__ import annotations

import re
from dataclasses import dataclass

from user_profile import Profile

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEALS = ["Breakfast", "Lunch", "Snack", "Dinner"]

NON_VEG = ["egg", "fish", "chicken", "mutton", "prawn", "meat", "gelatin", "beef", "pork"]
AVOID_INGREDIENTS = ["quinoa", "avocado", "kale", "chia", "flaxseed", "almond milk",
                     "protein powder", "olive oil", "overnight oats"]
AVOID_FRAMING = ["detox", "flush fat", "cheat day", "burn belly fat", "guaranteed"]
FRIED_OR_REFINED = ["vada", "bonda", "poori", "puri", "maida"]
ONION_GARLIC = ["onion", "garlic"]


@dataclass
class Report:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_table(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _has(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}", text, re.IGNORECASE) is not None


def validate(text: str, profile: Profile) -> Report:
    errors: list[str] = []
    warnings: list[str] = []

    rows = parse_table(text)
    if not rows:
        return Report(["No markdown table found"], [])
    header, body = rows[0], rows[1:]
    if [h.lower() for h in header] != ["day", "meal", "dish", "portion"]:
        errors.append(f"Header must be Day | Meal | Dish | Portion, got {header}")
    if len(body) != 28:
        errors.append(f"Expected 28 rows, found {len(body)}")
    for i, r in enumerate(body, 1):
        if len(r) != 4:
            errors.append(f"Row {i} has {len(r)} columns, expected 4")

    expected = [(d, m) for d in DAYS for m in MEALS]
    for i, (r, exp) in enumerate(zip(body, expected), 1):
        if len(r) >= 2 and (r[0].replace("*", ""), r[1].replace("*", "")) != exp:
            errors.append(f"Row {i} should be {exp[0]} {exp[1]}, got {r[0]} {r[1]}")

    # Ingredient checks run on dish text only (not the notes, which may say "no egg").
    dish_text = " ".join(r[2] for r in body if len(r) >= 3)
    for term in NON_VEG + AVOID_INGREDIENTS:
        if _has(term, dish_text):
            errors.append(f"Disallowed ingredient in plan: {term}")
    for term in profile.allergy_terms:
        if _has(term, dish_text):
            errors.append(f"Allergen in plan: {term}")
    for term in profile.dislike_terms:
        if _has(term, dish_text):
            errors.append(f"Disliked ingredient in plan: {term}")
    for term in AVOID_FRAMING:
        if _has(term, text):
            errors.append(f"Crash-diet wording: {term}")
    for term in FRIED_OR_REFINED:
        if _has(term, dish_text):
            warnings.append(f"Fried/refined item present (max one small fried serving): {term}")

    for day in profile.no_onion_garlic_days:
        for r in body:
            if len(r) >= 3 and r[0].replace("*", "") == day:
                for term in ONION_GARLIC:
                    if _has(term, r[2]):
                        errors.append(f"{day} {r[1]} contains {term}")

    # Repetition: same Dish text more than twice.
    seen: dict[str, int] = {}
    for r in body:
        if len(r) >= 3:
            seen[r[2].lower()] = seen.get(r[2].lower(), 0) + 1
    for dish, n in seen.items():
        if n > 2:
            warnings.append(f"Dish repeated {n} times: {dish}")

    notes = text.split("Notes", 1)[-1] if "Notes" in text else ""
    bullets = [l for l in notes.splitlines() if l.strip().startswith(("-", "*"))]
    if not notes:
        errors.append("Missing Notes section")
    elif len(bullets) > 5:
        errors.append(f"Notes has {len(bullets)} bullets, max 5")
    if notes and "dietitian" not in notes.lower():
        warnings.append("Notes should mention reviewing with a dietitian")

    return Report(errors, warnings)
