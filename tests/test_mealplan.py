from pathlib import Path

from user_profile import Profile
from prompt import build_prompt
from validate import DAYS, MEALS, validate

ROOT = Path(__file__).resolve().parent.parent
A = Profile.from_json(ROOT / "profiles" / "run_a.json")
B = Profile.from_json(ROOT / "profiles" / "run_b.json")


def make_plan(dish="Ragi dosa with pudina chutney", notes=None):
    rows = ["| Day | Meal | Dish | Portion |", "|---|---|---|---|"]
    for i, d in enumerate(DAYS):
        for m in MEALS:
            rows.append(f"| {d} | {m} | {dish} {i}{m} | 2 |")
    notes = notes or ["- Maintenance ~2,300 kcal", "- Prep dal on Sunday", "- Draft; review with a dietitian"]
    return "\n".join(rows) + "\n\nNotes\n" + "\n".join(notes)


def test_offline_generator_passes_validation_for_both_profiles():
    from cli import _render
    from planner import generate
    for p in (A, B):
        rep = validate(_render(generate(p)), p)
        assert rep.ok, rep.errors
        assert not rep.warnings, rep.warnings


def test_prompt_contains_profile_and_no_placeholder():
    p = build_prompt(B)
    assert "{{FOR_BLOCK}}" not in p
    assert "Chennai" in p and "Peanut and all nuts" in p


def test_calorie_estimate_respects_floor():
    lo, hi = A.target_range()
    assert lo >= 1500 and lo <= hi
    assert B.target_range()[0] >= 1200


def test_valid_plan_passes():
    assert validate(make_plan(), A).ok


def test_wrong_row_count_fails():
    plan = "\n".join(make_plan().splitlines()[:-6])
    assert not validate(plan, A).ok


def test_allergen_detected():
    assert not validate(make_plan("Peanut chutney idli"), B).ok


def test_dislike_detected():
    assert not validate(make_plan("Brinjal curry"), A).ok


def test_onion_on_monday_detected():
    plan = make_plan().replace("Monday | Lunch | Ragi dosa with pudina chutney 0Lunch",
                               "Monday | Lunch | Onion sambar")
    rep = validate(plan, B)
    assert any("Monday Lunch contains onion" in e for e in rep.errors)


def test_too_many_note_bullets():
    assert not validate(make_plan(notes=["- a"] * 6), A).ok
