#!/usr/bin/env python3
"""
Rename experiment course-spec files to <COURSE_CODE>.md so filenames no
longer leak the expected result or injected defect (Baseline vs Plugin
experiment data-leakage prevention).

Usage:
    python scripts/rename_test_cases.py --dry-run
    python scripts/rename_test_cases.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

COURSES_DIR = Path(__file__).resolve().parent.parent / "courses"
GOLD_LABELS_NAME = "gold-labels.json"

COURSE_CODE_RE = re.compile(r"\*\*Course Code:\*\*\s*([A-Za-z0-9_-]+)")


def discover_candidate_files(courses_dir: Path):
    """Return (candidates, skipped) — files eligible for renaming vs. not."""
    candidates = []
    skipped = []
    for entry in sorted(courses_dir.iterdir()):
        if entry.is_dir():
            continue
        if entry.name.startswith("."):
            skipped.append(entry.name)
            continue
        if entry.name == GOLD_LABELS_NAME:
            skipped.append(entry.name)
            continue
        if entry.suffix != ".md":
            skipped.append(entry.name)
            continue
        candidates.append(entry)
    return candidates, skipped


def extract_course_code(path: Path):
    text = path.read_text(encoding="utf-8")
    match = COURSE_CODE_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def plan_renames(candidates):
    """
    Returns (plan, errors) where plan is a list of (old_path, new_name, course_code)
    and errors is a list of human-readable conflict descriptions.
    """
    errors = []
    code_to_files = {}
    extraction_failures = []

    for path in candidates:
        code = extract_course_code(path)
        if code is None:
            extraction_failures.append(path.name)
            continue
        code_to_files.setdefault(code, []).append(path)

    if extraction_failures:
        errors.append(
            "Could not extract Course Code from: " + ", ".join(sorted(extraction_failures))
        )

    # Duplicate course codes among source files
    duplicates = {code: paths for code, paths in code_to_files.items() if len(paths) > 1}
    for code, paths in sorted(duplicates.items()):
        names = ", ".join(p.name for p in paths)
        errors.append(f"Duplicate Course Code '{code}' found in: {names}")

    # Build the plan only from non-duplicate, successfully-extracted codes
    plan = []
    dest_names = {}
    for code, paths in code_to_files.items():
        if code in duplicates:
            continue
        (path,) = paths
        new_name = f"{code}.md"
        plan.append((path, new_name, code))
        dest_names.setdefault(new_name, []).append(path.name)

    # Destination filename conflicts (two different sources mapping to the same
    # destination — shouldn't happen given the duplicate check above, but also
    # catches a destination colliding with a file NOT in the rename set at all)
    for new_name, sources in dest_names.items():
        if len(sources) > 1:
            errors.append(
                f"Destination conflict: {', '.join(sources)} would all rename to {new_name}"
            )

    all_source_names = {p.name for p in candidates}
    for path, new_name, code in plan:
        if new_name == path.name:
            continue  # already correctly named, no-op
        dest_path = path.parent / new_name
        if dest_path.exists() and new_name not in all_source_names:
            errors.append(
                f"Destination conflict: {new_name} already exists and is not part of the rename set"
            )

    return plan, errors


def update_gold_labels(courses_dir: Path, rename_map: dict, dry_run: bool):
    """rename_map: old filename -> new filename. Preserves all other fields."""
    gold_path = courses_dir / GOLD_LABELS_NAME
    if not gold_path.exists():
        return None

    with gold_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False
    for case in data.get("cases", []):
        old_file = case.get("file")
        if old_file in rename_map:
            case["file"] = rename_map[old_file]
            changed = True

    if not changed:
        return None

    if not dry_run:
        with gold_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    return gold_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned renames without changing any files.",
    )
    args = parser.parse_args()

    if not COURSES_DIR.is_dir():
        print(f"error: courses directory not found at {COURSES_DIR}", file=sys.stderr)
        sys.exit(1)

    candidates, skipped = discover_candidate_files(COURSES_DIR)
    plan, errors = plan_renames(candidates)

    if errors:
        print("Aborting: conflicts detected before any files were touched.\n")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    actionable = [(p, n, c) for (p, n, c) in plan if p.name != n]
    no_op = [(p, n, c) for (p, n, c) in plan if p.name == n]

    rename_map = {p.name: n for (p, n, c) in actionable}

    if args.dry_run:
        print("[DRY RUN] No files will be changed.\n")

    print("Renamed:" if not args.dry_run else "Would rename:")
    for path, new_name, _code in actionable:
        print(f"{path.name} -> {new_name}")
        if not args.dry_run:
            path.rename(path.parent / new_name)

    gold_path = update_gold_labels(COURSES_DIR, rename_map, dry_run=args.dry_run)

    print("\nSkipped:")
    for name in skipped:
        print(name)
    for path, new_name, _code in no_op:
        print(f"{path.name} (already named correctly)")

    if gold_path is not None:
        verb = "Would update" if args.dry_run else "Updated"
        print(f"\n{verb} {gold_path.name} file references for renamed cases.")


if __name__ == "__main__":
    main()
