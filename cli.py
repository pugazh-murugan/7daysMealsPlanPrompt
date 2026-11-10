"""Command line: mealplan prompt|run|validate."""
from __future__ import annotations

import argparse
import csv
import html
import json
import webbrowser
import sys
from pathlib import Path

from user_profile import Profile
from prompt import build_prompt
from planner import generate
from validate import parse_table, validate

DEFAULT_MODEL = "claude-sonnet-5-5"


def _generate(prompt: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        sys.exit("Install the LLM extra: pip install -e .[llm]")
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _to_json(text: str) -> dict:
    rows = parse_table(text)[1:]
    meals = [{"day": r[0], "meal": r[1], "dish": r[2], "portion": r[3]} for r in rows if len(r) == 4]
    notes = text.split("Notes", 1)[-1] if "Notes" in text else ""
    bullets = [l.strip().lstrip("-* ").strip() for l in notes.splitlines() if l.strip().startswith(("-", "*"))]
    return {"meals": meals, "notes": bullets}


def _render(data: dict) -> str:
    """Canonical output format: one 4-column table, then a Notes section."""
    lines = ["| Day | Meal | Dish | Portion |", "|---|---|---|---|"]
    for m in data["meals"]:
        lines.append(f"| {m['day']} | {m['meal']} | {m['dish']} | {m['portion']} |")
    lines += ["", "Notes"] + [f"- {n}" for n in data["notes"]]
    return "\n".join(lines) + "\n"


def _html(data: dict, title: str) -> str:
    esc = html.escape
    rows = "".join(
        f"<tr><td>{esc(m['day'])}</td><td>{esc(m['meal'])}</td>"
        f"<td>{esc(m['dish'])}</td><td>{esc(m['portion'])}</td></tr>"
        for m in data["meals"]
    )
    notes = "".join(f"<li>{esc(n)}</li>" for n in data["notes"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}
th{{background:#2e7d32;color:#fff}}tr:nth-child(even){{background:#f4f8f4}}</style></head>
<body><h1>{esc(title)}</h1>
<table><tr><th>Day</th><th>Meal</th><th>Dish</th><th>Portion</th></tr>{rows}</table>
<h2>Notes</h2><ul>{notes}</ul></body></html>"""


def _save(text: str, stem: str) -> list[Path]:
    data = _to_json(text)
    out = Path("output")
    out.mkdir(exist_ok=True)
    md, js, cs = out / f"{stem}.md", out / f"{stem}.json", out / f"{stem}.csv"
    page = out / f"{stem}.html"
    page.write_text(_html(data, "7-Day Meal Plan"), encoding="utf-8")
    md.write_text(_render(data), encoding="utf-8")
    js.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    with cs.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Day", "Meal", "Dish", "Portion"])
        w.writerows([m["day"], m["meal"], m["dish"], m["portion"]] for m in data["meals"])
    return [md, js, cs, page]


def _open(files: list[Path]) -> None:
    page = next(f for f in files if f.suffix == ".html")
    webbrowser.open(page.resolve().as_uri())


def _report(text: str, profile: Profile) -> int:
    rep = validate(text, profile)
    lo, hi = profile.target_range()
    print(f"\nReference: maintenance ~{profile.maintenance_kcal()} kcal, "
          f"target ~{lo}-{hi} kcal (floor {profile.calorie_floor})", file=sys.stderr)
    for w in rep.warnings:
        print(f"WARN  {w}", file=sys.stderr)
    for e in rep.errors:
        print(f"FAIL  {e}", file=sys.stderr)
    print("PASS" if rep.ok else "FAILED", file=sys.stderr)
    return 0 if rep.ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mealplan")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("prompt", help="print the rendered prompt")
    sp.add_argument("profile")

    sr = sub.add_parser("run", help="send the prompt to Claude and validate the result")
    sr.add_argument("profile")
    sr.add_argument("-o", "--output", help="file name stem inside output/ (default: <profile>_plan)")
    sr.add_argument("--model", default=DEFAULT_MODEL)
    sr.add_argument("--open", action="store_true", help="open the HTML plan in the browser")

    sg = sub.add_parser("generate", help="build the plan offline (no API key) and save files")
    sg.add_argument("profile")
    sg.add_argument("-o", "--output", help="file name stem inside output/ (default: <profile>_plan)")
    sg.add_argument("--open", action="store_true", help="open the HTML plan in the browser")

    sv = sub.add_parser("validate", help="validate an existing plan file")
    sv.add_argument("profile")
    sv.add_argument("plan")

    a = p.parse_args(argv)
    profile = Profile.from_json(a.profile)

    if a.cmd == "prompt":
        print(build_prompt(profile))
        return 0
    if a.cmd == "generate":
        text = _render(generate(profile))
        files = _save(text, a.output or f"{Path(a.profile).stem}_plan")
        print(text)
        print("Saved: " + ", ".join(str(f) for f in files), file=sys.stderr)
        if a.open:
            _open(files)
        return _report(text, profile)
    if a.cmd == "run":
        text = _generate(build_prompt(profile), a.model)
        stem = a.output or f"{Path(a.profile).stem}_plan"
        files = _save(text, stem)
        print(_render(_to_json(text)))
        print("Saved: " + ", ".join(str(f) for f in files), file=sys.stderr)
        if a.open:
            _open(files)
        return _report(text, profile)
    text = Path(a.plan).read_text(encoding="utf-8")
    return _report(text, profile)


if __name__ == "__main__":
    raise SystemExit(main())
