#!/usr/bin/env python3
"""Validate the generated Fat Shiba dictionary data without changing outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEVEL_ORDER = ("N5", "N4", "N3", "N2", "N1")
REQUIRED_WORD_FIELDS = ("id", "reading", "writing", "normalizedReading", "playReading", "zh", "level", "script")
EXAMPLE_FIELDS = ("id", "example_ja", "example_zh")


@dataclass(frozen=True)
class WordIssue:
    kind: str
    level: str
    word_id: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate current generated word-level and word metadata files."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root. Defaults to the repository root inferred from this script.",
    )
    parser.add_argument(
        "--level",
        choices=LEVEL_ORDER,
        help="Limit missing-example listing to one JLPT level.",
    )
    parser.add_argument(
        "--list-missing-examples",
        action="store_true",
        help="Print words that currently have no generated metadata example.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum missing-example rows to print. Use 0 for all rows.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "tsv"),
        default="text",
        help="Output format for --list-missing-examples.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when warnings are found, not only hard data errors.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Required file not found: {path}") from error


def load_level_words(web_data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    words_by_level: dict[str, list[dict[str, Any]]] = {}
    for level in LEVEL_ORDER:
        path = web_data_dir / f"word-level-{level.lower()}.js"
        text = read_text(path)
        match = re.search(
            rf"window\.FAT_SHIBA_WORD_LEVELS\.{level}\s*=\s*(\[.*\]);\s*$",
            text,
            flags=re.S,
        )
        if not match:
            raise ValueError(f"Cannot find generated word array in {path}")
        words_by_level[level] = json.loads(match.group(1))
    return words_by_level


def load_word_meta(web_data_dir: Path) -> dict[str, dict[str, Any]]:
    split_paths = {
        level: web_data_dir / f"word-meta-{level.lower()}.js"
        for level in LEVEL_ORDER
    }
    if all(path.exists() for path in split_paths.values()):
        merged: dict[str, dict[str, Any]] = {}
        for level, path in split_paths.items():
            text = read_text(path)
            match = re.search(
                rf"window\.FAT_SHIBA_WORD_META_BY_LEVEL\.{level}\s*=\s*(\{{.*\}});\s*Object\.assign",
                text,
                flags=re.S,
            )
            if not match:
                raise ValueError(f"Cannot find generated {level} metadata object in {path}")
            merged.update(json.loads(match.group(1)))
        return merged

    path = web_data_dir / "word_meta.js"
    text = read_text(path)
    match = re.search(r"window\.FAT_SHIBA_WORD_META\s*=\s*(\{.*\});\s*$", text, flags=re.S)
    if not match:
        raise ValueError(f"Cannot find generated metadata object in {path}")
    return json.loads(match.group(1))


def has_complete_example(meta_item: dict[str, Any] | None) -> bool:
    if not meta_item:
        return False
    examples = meta_item.get("examples")
    if not isinstance(examples, list):
        return False
    for example in examples:
        if not isinstance(example, dict):
            continue
        if str(example.get("ja") or "").strip() and str(example.get("zh") or "").strip():
            return True
    return False


def word_display(word: dict[str, Any]) -> str:
    writing = str(word.get("writing") or "").strip()
    reading = str(word.get("reading") or "").strip()
    if writing and reading and writing != reading:
        return f"{writing}（{reading}）"
    return writing or reading or str(word.get("playReading") or "").strip()


def validate_words(words_by_level: dict[str, list[dict[str, Any]]]) -> list[WordIssue]:
    issues: list[WordIssue] = []
    all_ids: list[str] = []
    keys: list[tuple[str, str]] = []

    for level, words in words_by_level.items():
        for index, word in enumerate(words, start=1):
            word_id = str(word.get("id") or "").strip()
            all_ids.append(word_id)
            keys.append((str(word.get("playReading") or ""), str(word.get("writing") or "")))

            for field in REQUIRED_WORD_FIELDS:
                if str(word.get(field) or "").strip() == "":
                    issues.append(WordIssue("missing_word_field", level, word_id, f"row {index}: missing {field}"))

            declared_level = str(word.get("level") or "").strip()
            if declared_level and declared_level != level:
                issues.append(
                    WordIssue("level_mismatch", level, word_id, f"row {index}: word.level is {declared_level}")
                )

    for word_id, count in Counter(all_ids).items():
        if not word_id:
            continue
        if count > 1:
            issues.append(WordIssue("duplicate_word_id", "", word_id, f"appears {count} times"))

    for (play_reading, writing), count in Counter(keys).items():
        if not play_reading and not writing:
            continue
        if count > 1:
            issues.append(
                WordIssue("duplicate_play_reading_writing", "", "", f"{play_reading} / {writing}: {count} rows")
            )

    return issues


def load_manual_example_stats(
    project_root: Path,
    dictionary_dir: Path,
    word_ids: set[str],
) -> tuple[list[str], dict[str, dict[str, int]]]:
    warnings: list[str] = []
    stats: dict[str, dict[str, int]] = {}

    for path in sorted(dictionary_dir.glob("n*_examples.csv")):
        level = path.stem.split("_", 1)[0].upper()
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            fieldnames = tuple(reader.fieldnames or ())
            rows = list(reader)

        if fieldnames != EXAMPLE_FIELDS:
            warnings.append(f"{path.relative_to(project_root)}: unexpected fields {fieldnames}")

        ids = [str(row.get("id") or "").strip() for row in rows]
        duplicate_count = sum(1 for _, count in Counter(ids).items() if count > 1)
        blank_id_count = sum(1 for word_id in ids if not word_id)
        unknown_count = sum(1 for word_id in ids if word_id and word_id not in word_ids)
        blank_example_count = sum(
            1
            for row in rows
            if not str(row.get("example_ja") or "").strip() or not str(row.get("example_zh") or "").strip()
        )

        stats[level] = {
            "rows": len(rows),
            "unique_ids": len(set(ids) - {""}),
            "duplicate_ids": duplicate_count,
            "blank_ids": blank_id_count,
            "unknown_ids": unknown_count,
            "blank_examples": blank_example_count,
        }

    return warnings, stats


def collect_missing_examples(
    words_by_level: dict[str, list[dict[str, Any]]],
    meta: dict[str, dict[str, Any]],
    level_filter: str | None = None,
) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for level in LEVEL_ORDER:
        if level_filter and level != level_filter:
            continue
        for word in words_by_level[level]:
            word_id = str(word.get("id") or "").strip()
            if has_complete_example(meta.get(word_id)):
                continue
            missing.append({
                "level": level,
                "id": word_id,
                "display": word_display(word),
                "reading": str(word.get("reading") or "").strip(),
                "writing": str(word.get("writing") or "").strip(),
                "zh": str(word.get("zh") or "").strip(),
                "source": "eggrolls" if "_egg_" in word_id else "core",
            })
    return missing


def print_table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))

    print("  " + "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  " + "  ".join("-" * width for width in widths))
    for row in rows:
        print("  " + "  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def print_missing_examples(rows: list[dict[str, str]], output_format: str, limit: int) -> None:
    display_rows = rows if limit == 0 else rows[:limit]

    if output_format == "tsv":
        print("\t".join(("level", "id", "display", "reading", "writing", "zh", "source")))
        for row in display_rows:
            print("\t".join(row[key] for key in ("level", "id", "display", "reading", "writing", "zh", "source")))
        return

    for row in display_rows:
        print(f"  {row['level']} {row['id']}  {row['display']}  - {row['zh']} [{row['source']}]")


def manual_example_issue_count(
    manual_example_stats: dict[str, dict[str, int]],
    stat_name: str,
) -> int:
    return sum(stats[stat_name] for stats in manual_example_stats.values())


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    web_data_dir = project_root / "web" / "data"
    dictionary_dir = project_root / "tools" / "dictionary"

    words_by_level = load_level_words(web_data_dir)
    meta = load_word_meta(web_data_dir)
    all_words = [word for level in LEVEL_ORDER for word in words_by_level[level]]
    word_ids = {str(word.get("id") or "").strip() for word in all_words if str(word.get("id") or "").strip()}

    word_issues = validate_words(words_by_level)
    manual_warnings, manual_example_stats = load_manual_example_stats(project_root, dictionary_dir, word_ids)
    all_missing_examples = collect_missing_examples(words_by_level, meta)
    listed_missing_examples = [
        row for row in all_missing_examples
        if not args.level or row["level"] == args.level
    ]
    missing_examples_by_level = Counter(row["level"] for row in all_missing_examples)
    missing_meta_by_level: dict[str, int] = {}
    unknown_meta_ids = sorted(word_id for word_id in meta if word_id not in word_ids)

    for level in LEVEL_ORDER:
        missing_meta_by_level[level] = sum(
            1
            for word in words_by_level[level]
            if str(word.get("id") or "").strip() not in meta
        )

    print("Dictionary validation")
    print(f"Project root: {project_root}")
    print()

    coverage_rows: list[tuple[Any, ...]] = []
    for level in LEVEL_ORDER:
        words = words_by_level[level]
        ids = [str(word.get("id") or "").strip() for word in words]
        meta_count = sum(1 for word_id in ids if word_id in meta)
        example_count = sum(1 for word_id in ids if has_complete_example(meta.get(word_id)))
        coverage_rows.append((
            level,
            len(words),
            meta_count,
            example_count,
            missing_meta_by_level[level],
            missing_examples_by_level[level],
        ))

    print("Generated coverage:")
    print_table(("level", "words", "meta", "examples", "missing_meta", "missing_examples"), coverage_rows)
    print()

    print("Manual example CSVs:")
    manual_rows = [
        (
            level,
            stats["rows"],
            stats["unique_ids"],
            stats["duplicate_ids"],
            stats["unknown_ids"],
            stats["blank_examples"],
        )
        for level, stats in sorted(manual_example_stats.items())
    ]
    if manual_rows:
        print_table(("level", "rows", "unique_ids", "dup_ids", "unknown_ids", "blank_examples"), manual_rows)
    else:
        print("  No n*_examples.csv files found.")
    print()

    print("Issues:")
    issue_counts = Counter(issue.kind for issue in word_issues)
    if unknown_meta_ids:
        issue_counts["unknown_meta_id"] = len(unknown_meta_ids)
    if manual_warnings:
        issue_counts["manual_example_warning"] = len(manual_warnings)
    manual_hard_issue_names = (
        ("manual_example_duplicate_id", "duplicate_ids"),
        ("manual_example_blank_id", "blank_ids"),
        ("manual_example_unknown_id", "unknown_ids"),
    )
    manual_soft_issue_names = (
        ("manual_example_blank_example", "blank_examples"),
    )
    for issue_name, stat_name in manual_hard_issue_names + manual_soft_issue_names:
        count = manual_example_issue_count(manual_example_stats, stat_name)
        if count:
            issue_counts[issue_name] = count

    if issue_counts:
        for kind, count in sorted(issue_counts.items()):
            print(f"  {kind}: {count}")
        for issue in word_issues[:10]:
            location = f"{issue.level} {issue.word_id}".strip()
            print(f"  - {issue.kind}: {location} {issue.message}".rstrip())
        for warning in manual_warnings[:10]:
            print(f"  - manual_example_warning: {warning}")
        for word_id in unknown_meta_ids[:10]:
            print(f"  - unknown_meta_id: {word_id}")
    else:
        print("  No hard structural issues found.")
    print()

    total_missing_examples = len(listed_missing_examples)
    level_note = f" for {args.level}" if args.level else ""
    print(f"Missing examples{level_note}: {total_missing_examples}")
    if total_missing_examples and not args.list_missing_examples:
        print("  Use --list-missing-examples to print rows, or --list-missing-examples --limit 0 for all rows.")

    if args.list_missing_examples:
        print_missing_examples(listed_missing_examples, args.format, args.limit)
        if args.limit and total_missing_examples > args.limit:
            print(f"  ... {total_missing_examples - args.limit} more not shown. Use --limit 0 to show all.")

    manual_hard_errors = any(
        stats["duplicate_ids"] or stats["blank_ids"] or stats["unknown_ids"]
        for stats in manual_example_stats.values()
    )
    manual_soft_warnings = any(
        stats["blank_examples"]
        for stats in manual_example_stats.values()
    )

    has_hard_errors = bool(word_issues or unknown_meta_ids or manual_hard_errors)
    has_warnings = bool(
        manual_warnings
        or manual_soft_warnings
        or all_missing_examples
        or any(missing_meta_by_level.values())
    )
    if has_hard_errors or (args.strict and has_warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
