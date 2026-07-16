#!/usr/bin/env python3
"""Convert OCR vocabulary candidates into a manual-review CSV.

The extractor produces generic candidate columns named headword/bracket.
This script reshapes those rows into the same reading/writing style used by
the corrected wordlists, while flagging rows that likely need human review.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_candidates.csv"
DEFAULT_OUTPUT = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_for_review.csv"

SUSPICIOUS_READING_RE = re.compile(
    r"[0-9]|N1|章|パート|バート|Memo|索引|分類|用語|語$|^[^ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z]+$"
)
SUSPICIOUS_WRITING_RE = re.compile(r"^[0-9]+$|^$")

FIELDS = [
    "level",
    "reading",
    "writing",
    "page",
    "column",
    "entry_no",
    "needs_review",
    "review_reason",
    "ocr_context",
]


def review_reasons(reading: str, writing: str, entry_no: str) -> list[str]:
    reasons: list[str] = []
    if not writing:
        reasons.append("blank_writing")
    if not entry_no:
        reasons.append("blank_entry_no")
    if SUSPICIOUS_READING_RE.search(reading):
        reasons.append("suspicious_reading")
    if SUSPICIOUS_WRITING_RE.fullmatch(writing):
        reasons.append("suspicious_writing")
    if len(reading) > 24 or len(writing) > 60:
        reasons.append("too_long")
    return reasons


def convert(source: Path, output: Path) -> Counter[str]:
    reason_counts: Counter[str] = Counter()
    output.parent.mkdir(parents=True, exist_ok=True)

    with source.open(newline="", encoding="utf-8") as source_handle, output.open(
        "w", newline="", encoding="utf-8"
    ) as output_handle:
        reader = csv.DictReader(source_handle)
        writer = csv.DictWriter(output_handle, fieldnames=FIELDS)
        writer.writeheader()

        for row in reader:
            reading = (row.get("headword") or "").strip()
            writing = (row.get("bracket") or "").strip()
            entry_no = (row.get("entry_no") or "").strip()
            reasons = review_reasons(reading, writing, entry_no)
            reason_counts.update(reasons)

            writer.writerow(
                {
                    "level": row.get("level", ""),
                    "reading": reading,
                    "writing": writing,
                    "page": row.get("page", ""),
                    "column": row.get("column", ""),
                    "entry_no": entry_no,
                    "needs_review": "1" if reasons else "",
                    "review_reason": ";".join(dict.fromkeys(reasons)),
                    "ocr_context": row.get("ocr_context", ""),
                }
            )

    return reason_counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    reason_counts = convert(args.source, args.output)
    print(f"Wrote review CSV to {args.output}")
    print(f"Review reason counts: {dict(reason_counts)}")


if __name__ == "__main__":
    main()
