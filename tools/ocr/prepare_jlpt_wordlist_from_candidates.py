#!/usr/bin/env python3
"""Prepare an OCR candidate CSV for manual JLPT word-list correction.

This converts the broader candidate format produced by
extract_jlpt_vocab_from_pdf.py into the compact correction format used by the
dictionary CSVs:

level,reading,writing,page,column,entry_no,needs_review
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_candidates.csv"
DEFAULT_OUTPUT = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_corrected.csv"
DEFAULT_REVIEW_OUTPUT = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_needs_review.csv"

KANA_RE = re.compile(r"^[ぁ-んァ-ヶー・、（）()]+$")
KATAKANA_RE = re.compile(r"^[ァ-ヶー・、（）()]+$")
ASCII_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 .,+/&'()\\-]*$")
JAPANESE_WRITING_RE = re.compile(r"^[ぁ-んァ-ヶー一-龯々〆ヵヶ・、（）()]+$")
OCR_ARTIFACT_RE = re.compile(r"[|｜{}\[\]<>$#=~^_@]|[A-Za-z0-9]{2,}")


def nfkc(value: str | None) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip())


def compact(value: str) -> str:
    value = nfkc(value)
    value = re.sub(r"\s+", "", value)
    value = value.strip(" |:;。・,，.「」『』")
    return value


def clean_reading(value: str) -> str:
    value = compact(value)
    value = value.replace("[", "【").replace("]", "】")
    value = value.strip("【】")
    return value


def clean_writing(value: str, reading: str) -> str:
    value = compact(value)
    value = value.replace("[", "【").replace("]", "】")
    value = value.strip("【】")
    if not value:
        return reading
    return value


def review_reasons(reading: str, writing: str) -> list[str]:
    reasons: list[str] = []
    if not reading:
        reasons.append("blank_reading")
    elif not KANA_RE.fullmatch(reading):
        reasons.append("reading_has_non_kana")

    if not writing:
        reasons.append("blank_writing")
    elif KATAKANA_RE.fullmatch(reading):
        if writing != reading and not (ASCII_RE.fullmatch(writing) or JAPANESE_WRITING_RE.fullmatch(writing)):
            reasons.append("suspicious_katakana_writing")
    elif not JAPANESE_WRITING_RE.fullmatch(writing):
        reasons.append("writing_has_unexpected_chars")

    if OCR_ARTIFACT_RE.search(reading):
        reasons.append("reading_has_ocr_artifact")
    if OCR_ARTIFACT_RE.search(writing) and not ASCII_RE.fullmatch(writing):
        reasons.append("writing_has_ocr_artifact")
    if len(reading) > 24:
        reasons.append("long_reading")
    if len(writing) > 32:
        reasons.append("long_writing")
    if reading.count("(") != reading.count(")") or writing.count("(") != writing.count(")"):
        reasons.append("unbalanced_parentheses")
    if reading.count("【") != reading.count("】") or writing.count("【") != writing.count("】"):
        reasons.append("unbalanced_brackets")
    return reasons


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        fields = ["level", "reading", "writing", "page", "column", "entry_no", "needs_review"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def convert(input_path: Path, output_path: Path, review_output_path: Path | None) -> tuple[int, int]:
    output_rows: list[dict[str, str]] = []
    with input_path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            reading = clean_reading(row.get("headword", ""))
            writing = clean_writing(row.get("bracket", ""), reading)
            reasons = review_reasons(reading, writing)
            output_rows.append(
                {
                    "level": nfkc(row.get("level", "")),
                    "reading": reading,
                    "writing": writing,
                    "page": nfkc(row.get("page", "")),
                    "column": nfkc(row.get("column", "")),
                    "entry_no": nfkc(row.get("entry_no", "")),
                    "needs_review": ";".join(reasons),
                }
            )

    write_rows(output_path, output_rows)
    if review_output_path:
        write_rows(review_output_path, [row for row in output_rows if row["needs_review"]])
    review_count = sum(1 for row in output_rows if row["needs_review"])
    return len(output_rows), review_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    args = parser.parse_args()

    total, review_count = convert(args.input, args.output, args.review_output)
    print(f"wrote={total}")
    print(f"needs_review={review_count}")
    print(f"output={args.output}")
    print(f"review_output={args.review_output}")


if __name__ == "__main__":
    main()
