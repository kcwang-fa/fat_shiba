#!/usr/bin/env python3
"""Prepare review-friendly N2 vocabulary CSV from OCR candidates.

The OCR extractor writes raw rows as headword/bracket/context.  This script
keeps the source evidence but reshapes the data into the same review pattern
used by the existing N4 list: reading, writing, source page/column/entry no,
and a review flag for rows that are likely OCR noise.
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = TOOL_ROOT / "outputs" / "jlpt_n2_candidates_raw.csv"
DEFAULT_OUTPUT = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_candidates.csv"
DEFAULT_REVIEW_OUTPUT = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_needs_review.csv"


KANA_RE = re.compile(r"^[ぁ-んァ-ヶー・ー]+$")
READING_ALLOWED_RE = re.compile(r"^[ぁ-んァ-ヶー・ー（）()0-9A-Za-z]+$")
SUSPICIOUS_READING_RE = re.compile(r"[一-龯々〆]|[!#$%&=<>?@\\^_`{|}~]")
SUSPICIOUS_WRITING_RE = re.compile(r"[!#$%&=<>?@\\^_`{|}~]|[〇○●□■◆◇]")


def nfkc(value: str | None) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip())


def clean_reading(value: str) -> str:
    value = nfkc(value)
    value = re.sub(r"\s+", "", value)
    value = value.strip(" |:;。,.，、「」『』[]【】")
    value = value.replace("人", "")
    return value


def clean_writing(value: str) -> str:
    value = nfkc(value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" |:;。,.，、「」『』[]【】")
    return value


def normalize_entry_no(value: str) -> str:
    value = nfkc(value).lower()
    if not value:
        return ""
    value = value.replace("o", "0")
    if value.isdigit():
        return value.zfill(2)
    return value


def review_reasons(row: dict[str, str], reading: str, writing: str, seen: Counter[str]) -> list[str]:
    reasons: list[str] = []
    if not reading:
        reasons.append("blank_reading")
    if not writing:
        reasons.append("blank_writing")
    if reading and not READING_ALLOWED_RE.fullmatch(reading):
        reasons.append("unexpected_reading_chars")
    if reading and SUSPICIOUS_READING_RE.search(reading):
        reasons.append("suspicious_reading")
    if writing and SUSPICIOUS_WRITING_RE.search(writing):
        reasons.append("suspicious_writing")
    if reading and seen[reading] > 1:
        reasons.append("duplicate_reading")
    if row.get("headword", "") != reading:
        reasons.append("reading_auto_cleaned")
    return reasons


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare_rows(raw_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]], Counter[str]]:
    readings = Counter(clean_reading(row.get("headword", "")) for row in raw_rows)
    prepared: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    reason_counts: Counter[str] = Counter()

    for row in raw_rows:
        reading = clean_reading(row.get("headword", ""))
        writing = clean_writing(row.get("bracket", ""))
        reasons = review_reasons(row, reading, writing, readings)
        reason_text = ";".join(reasons)
        reason_counts.update(reasons)

        prepared_row = {
            "level": nfkc(row.get("level", "N2")) or "N2",
            "reading": reading,
            "writing": writing,
            "page": nfkc(row.get("page", "")),
            "column": nfkc(row.get("column", "")),
            "entry_no": normalize_entry_no(row.get("entry_no", "")),
            "needs_review": "1" if reasons else "",
            "review_reason": reason_text,
            "ocr_headword": nfkc(row.get("headword", "")),
            "ocr_bracket": nfkc(row.get("bracket", "")),
            "ocr_context": nfkc(row.get("ocr_context", "")),
        }
        prepared.append(prepared_row)
        if reasons:
            review_rows.append(prepared_row)

    return prepared, review_rows, reason_counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    args = parser.parse_args()

    raw_rows = read_rows(args.source)
    prepared, review_rows, reason_counts = prepare_rows(raw_rows)

    fieldnames = [
        "level",
        "reading",
        "writing",
        "page",
        "column",
        "entry_no",
        "needs_review",
        "review_reason",
        "ocr_headword",
        "ocr_bracket",
        "ocr_context",
    ]
    write_rows(args.output, prepared, fieldnames)
    write_rows(args.review_output, review_rows, fieldnames)

    print(f"source_rows={len(raw_rows)}")
    print(f"prepared_rows={len(prepared)}")
    print(f"needs_review={len(review_rows)}")
    for reason, count in sorted(reason_counts.items()):
        print(f"{reason}={count}")


if __name__ == "__main__":
    main()
