"""Offline plan generator: builds the 7-day plan from a built-in dish library.

No API key needed. Dishes are filtered by the profile (allergies, dislikes,
no-onion/garlic days) and rotated so no dish repeats within the week.
Flags: W = weekend only (longer cook), O = contains onion/garlic.
"""
from __future__ import annotations

import re

from user_profile import Profile

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# (dish, portion, flags)
BREAKFAST = [
    ("Ragi dosa, pudina chutney", "2 dosas, 2 tbsp", ""),
    ("Idli, vegetable sambar", "3 idlis, 1 katori", ""),
    ("Foxtail millet pongal, coconut chutney", "1 cup, 2 tbsp", ""),
    ("Moong dal cheela, mint chutney", "2 cheelas, 2 tbsp", ""),
    ("Ragi idli, tomato-coriander chutney", "3 idlis, 2 tbsp", ""),
    ("Vegetable little millet upma", "1 cup", "O"),
    ("Broken wheat (godhi) rava upma with vegetables", "1 cup", "O"),
    ("Pesarattu, ginger chutney", "2 pesarattu, 2 tbsp", "W"),
    ("Adai, coconut chutney", "2 adai, 2 tbsp", "W"),
]
LUNCH = [
    ("Brown rice, vegetable sambar, beans poriyal, curd",
     "1 cup, 1 katori, 1/2 cup, 1/2 cup", ""),
    ("Little millet curd rice, carrot poriyal, cucumber salad",
     "1 cup, 1/2 cup, 1 small bowl", ""),
    ("Red rice, keerai kootu, cabbage poriyal, buttermilk",
     "1 cup, 1 katori, 1/2 cup, 1 glass", ""),
    ("Phulka, dal palak, cabbage-carrot salad", "2 phulkas, 1 katori, 1 bowl", ""),
    ("Parboiled rice, drumstick sambar, ladies finger poriyal, buttermilk",
     "1 cup, 1 katori, 1/2 cup, 1 glass", ""),
    ("Kodo millet vegetable pulao, cucumber raita", "1 cup, 1/2 cup", "O"),
    ("Brown rice, moong dal, beetroot poriyal, curd",
     "1 cup, 1 katori, 1/2 cup, 1/2 cup", ""),
    ("Bisi bele bath with vegetables, cucumber raita", "1.5 cups, 1/2 cup", "W"),
    ("Rice, pumpkin sambar, raw banana poriyal, buttermilk",
     "1 cup, 1 katori, 1/2 cup, 1 glass", "W"),
]
SNACK = [
    ("Green moong sundal", "1 small bowl", ""),
    ("Roasted chana", "1/4 cup", ""),
    ("Banana, spiced buttermilk", "1 small banana, 1 glass", ""),
    ("Ragi malt without sugar", "1 glass", ""),
    ("Kala chana sundal with a little coconut", "1 small bowl", ""),
    ("Papaya or guava cubes, buttermilk", "1 small bowl, 1 glass", ""),
    ("Sprouts salad with lemon", "1 small bowl", ""),
    ("Cucumber and carrot sticks, mint curd dip", "1 bowl, 2 tbsp", ""),
    ("Groundnut sundal", "1 small bowl", ""),
    ("Roasted groundnuts", "a small handful", ""),
]
DINNER = [
    ("Ragi roti, peas-carrot kurma, curd", "2 rotis, 1 katori, 1/2 cup", ""),
    ("Plain dosa, vegetable sambar, tomato-coriander chutney",
     "2 dosas, 1 katori, 2 tbsp", ""),
    ("Little millet moong dal khichdi, cabbage poriyal, curd",
     "1 cup, 1/2 cup, 1/2 cup", ""),
    ("Chapati, sprouted moong curry, cucumber raita",
     "2 chapatis, 1 katori, 1/2 cup", ""),
    ("Moong dal vegetable soup, phulka, carrot-cucumber salad",
     "1 bowl, 2 phulkas, 1 small bowl", ""),
    ("Phulka, palak paneer, tomato-cucumber salad",
     "2 phulkas, 1 katori, 1 small bowl", "O"),
    ("Ragi idiyappam, vegetable kurma", "3 idiyappam, 1 katori", "O"),
    ("Adai, avial, curd", "2 adai, 1 katori, 1/2 cup", "W"),
    ("Kodo millet vegetable khichdi, beans poriyal, buttermilk",
     "1 cup, 1/2 cup, 1 glass", "W"),
]


def _hit(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}", text, re.IGNORECASE) is not None


def _pick(pool, day_idx, day, profile, used):
    banned = profile.allergy_terms + profile.dislike_terms
    weekend = day in ("Saturday", "Sunday")
    restricted = day in profile.no_onion_garlic_days
    ok = [
        (i, d) for i, d in enumerate(pool)
        if not any(_hit(t, d[0]) for t in banned)
        and not (d[2] == "W" and not weekend)
        and not (d[2] == "O" and restricted)
    ]
    n = len(pool)
    # least-used first; ties broken by rotating start so days differ
    i, dish = min(ok, key=lambda x: (used.get(x[0], 0), (x[0] - day_idx) % n))
    used[i] = used.get(i, 0) + 1
    return dish


def generate(profile: Profile) -> dict:
    pools = [("Breakfast", BREAKFAST), ("Lunch", LUNCH), ("Snack", SNACK), ("Dinner", DINNER)]
    used = {name: {} for name, _ in pools}
    meals = []
    for di, day in enumerate(DAYS):
        for name, pool in pools:
            dish, portion, _ = _pick(pool, di, day, profile, used[name])
            meals.append({"day": day, "meal": name, "dish": dish, "portion": portion})

    lo, hi = profile.target_range()
    notes = [
        f"Estimated maintenance about {profile.maintenance_kcal():,} kcal/day; "
        f"target about {lo:,}-{hi:,} kcal/day (not below {profile.calorie_floor:,}).",
        "Prep ahead on Sunday: cook dal, soak ragi/millets and batter, chop vegetables, "
        "and grind chutneys for 2-3 days.",
    ]
    if profile.no_onion_garlic_days:
        notes.append("No onion or garlic on " + " and ".join(profile.no_onion_garlic_days) + ".")
    if profile.allergy_terms:
        notes.append(f"Avoids: {profile.allergies}.")
    notes.append("This is a draft for discussion; review it with a qualified dietitian.")
    return {"meals": meals, "notes": notes}
