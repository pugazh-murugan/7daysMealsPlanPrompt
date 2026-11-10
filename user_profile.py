"""Person profile (the `# FOR` block) and calorie estimate."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Profile:
    age: int
    sex: str  # "Male" | "Female"
    height_cm: float
    weight_kg: float
    activity_level: str
    activity_factor: float  # 1.2 sedentary, 1.375 light, 1.55 moderate
    goal: str
    location: str
    weekday_cooking_time: str
    household: str
    diet_type: str
    allergies: str = "None"
    dislikes: str = "None"
    other_notes: str = ""
    # Machine-checkable fields used by the validator
    allergy_terms: list[str] = field(default_factory=list)
    dislike_terms: list[str] = field(default_factory=list)
    no_onion_garlic_days: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> "Profile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)

    @property
    def calorie_floor(self) -> int:
        return 1200 if self.sex.lower().startswith("f") else 1500

    def maintenance_kcal(self) -> int:
        """Mifflin-St Jeor BMR x activity factor."""
        s = 5 if self.sex.lower().startswith("m") else -161
        bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + s
        return round(bmr * self.activity_factor)

    def target_range(self) -> tuple[int, int]:
        m = self.maintenance_kcal()
        return max(m - 500, self.calorie_floor), max(m - 300, self.calorie_floor)

    def for_block(self) -> str:
        lines = [
            f"- Age: {self.age}",
            f"- Sex: {self.sex}",
            f"- Height / weight (optional): {self.height_cm:g} cm / {self.weight_kg:g} kg",
            f"- Activity level: {self.activity_level}",
            f"- Goal: {self.goal}",
            f"- Location / local food context: {self.location}",
            f"- Weekday cooking time: {self.weekday_cooking_time}",
            f"- Household: {self.household}",
            f"- Diet type: {self.diet_type}",
            f"- Allergies: {self.allergies}",
            f"- Dislikes: {self.dislikes}",
            f"- Other notes: {self.other_notes}",
        ]
        return "\n".join(lines)
