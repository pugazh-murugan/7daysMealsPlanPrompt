# 7-day meal plan

Python tooling around the 7-day South Indian vegetarian meal plan prompt
(`meal_plan_prompt.md`). It renders the prompt from a JSON profile, optionally
sends it to Claude, and validates the result against the prompt's own rules.

Output is a draft for discussion, not dietary advice.

## Setup

```
pip install -r requirements.txt pytest
```

## Usage

```
python cli.py prompt profiles/run_a.json            # print the rendered prompt
python cli.py run profiles/run_b.json -o planB.md   # needs ANTHROPIC_API_KEY
python cli.py validate profiles/run_b.json planB.md # check an existing plan
pytest
```

`run` and `validate` exit non-zero if a check fails.

## Validation checks

- 4 columns (`Day | Meal | Dish | Portion`), 28 rows, Monday-Sunday in order, meals in order
- No non-vegetarian items, no "avoid" ingredients, no crash-diet wording
- Profile allergens and dislikes (`allergy_terms`, `dislike_terms`) absent from every dish
- Onion/garlic absent on `no_onion_garlic_days`
- Notes section with at most 5 bullets, mentions a dietitian
- Warnings: fried/refined items, dish repeated more than twice

A Mifflin-St Jeor maintenance and target-kcal reference (respecting the 1,200 /
1,500 kcal floor) is printed alongside the report to compare with the model's
stated estimate. Calories in the plan itself are not computed.

## Profiles

Edit or copy `profiles/*.json`. Human-readable fields feed the `# FOR` block;
`allergy_terms`, `dislike_terms` and `no_onion_garlic_days` drive validation.
`run_a.json` and `run_b.json` are the two test variants from the original prompt.
