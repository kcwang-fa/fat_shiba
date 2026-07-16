#!/usr/bin/env python3
"""Clean the corrected N3 CSV and append safe rows into word data.

The source CSV comes from OCR, so this imports only rows that are low-risk for
the game and keeps the existing hand-written N3 rows first.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = Path(__file__).resolve().parent
DATA_PATH = PROJECT_ROOT / "web" / "data" / "word_data.js"
SOURCE_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_corrected.csv"
ZH_OVERRIDES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_zh_overrides.csv"
CLEANED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_cleaned_for_game.csv"
REJECTED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_rejected_for_game.csv"

N3_BLOCK_START = "  N3_EXTRA_WORD_ROWS_TEXT: `"
N3_BLOCK_END = "`,\n  N2_EXTRA_WORD_ROWS_TEXT"

HIRAGANA_RE = re.compile(r"^[ぁ-んー]+$")
KATAKANA_RE = re.compile(r"^[ァ-ヶー]+$")
ASCII_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z .,+/&'()\\-]*$")
JS_ROW_RE = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)


READING_CORRECTIONS = {
    "あっというま(に": "あっというまに",
    "かーぶ": "カーブ",
    "よごぎる": "よこぎる",
}

WRITING_CORRECTIONS = {
    ("あっというまに", "あっいう間(に)"): "あっという間に",
    ("そうちょう", "上早朝"): "早朝",
    ("こうそく", "高束"): "高速",
    ("ひく", "較く"): "轢く",
    ("よこぎる", "横切る"): "横切る",
}


def nfkc(value: str | None) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip())


def to_hiragana_char(char: str) -> str:
    code = ord(char)
    if 0x30A1 <= code <= 0x30F6:
        return chr(code - 0x60)
    return char


def kana_vowel(kana: str) -> str:
    vowels = {
        "あ": "a", "ぁ": "a", "か": "a", "が": "a", "さ": "a", "ざ": "a", "た": "a", "だ": "a", "な": "a", "は": "a", "ば": "a", "ぱ": "a", "ま": "a", "や": "a", "ゃ": "a", "ら": "a", "わ": "a",
        "い": "i", "ぃ": "i", "き": "i", "ぎ": "i", "し": "i", "じ": "i", "ち": "i", "ぢ": "i", "に": "i", "ひ": "i", "び": "i", "ぴ": "i", "み": "i", "り": "i",
        "う": "u", "ぅ": "u", "ゔ": "u", "く": "u", "ぐ": "u", "す": "u", "ず": "u", "つ": "u", "づ": "u", "ぬ": "u", "ふ": "u", "ぶ": "u", "ぷ": "u", "む": "u", "ゆ": "u", "ゅ": "u", "る": "u",
        "え": "e", "ぇ": "e", "け": "e", "げ": "e", "せ": "e", "ぜ": "e", "て": "e", "で": "e", "ね": "e", "へ": "e", "べ": "e", "ぺ": "e", "め": "e", "れ": "e",
        "お": "o", "ぉ": "o", "こ": "o", "ご": "o", "そ": "o", "ぞ": "o", "と": "o", "ど": "o", "の": "o", "ほ": "o", "ぼ": "o", "ぽ": "o", "も": "o", "よ": "o", "ょ": "o", "ろ": "o", "を": "o",
    }
    return vowels.get(to_hiragana_char(kana), "")


def normalize_kana_reading(value: str) -> str:
    output: list[str] = []
    for raw_char in nfkc(value):
        kana = to_hiragana_char(raw_char)
        if kana == "ー":
            long_vowel = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}.get(kana_vowel(output[-1]) if output else "")
            if long_vowel:
                output.append(long_vowel)
            continue
        output.append(kana)
    return "".join(output)


def parse_js_rows(block: str) -> list[tuple[str, str, str, str, str, str]]:
    return [match.groups() for match in JS_ROW_RE.finditer(block)]


def slice_between(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def extract_word_text_property(word_data: str, name: str) -> str:
    marker = f"  {name}: `"
    start = word_data.index(marker) + len(marker)
    end = word_data.index("`", start)
    return word_data[start:end]


def parse_pipe_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 5:
            raise ValueError(f"Invalid word row: {line}")
        reading, writing, declared, zh, script = parts
        rows.append(
            {
                "reading": reading,
                "writing": writing,
                "declaredNormalizedReading": declared,
                "zh": zh,
                "script": script,
                "source_page": "",
                "source_column": "",
                "source_entry_no": "",
                "source_writing": writing,
            }
        )
    return rows


def load_zh_overrides() -> dict[str, str]:
    if not ZH_OVERRIDES_CSV.exists():
        return {}

    with ZH_OVERRIDES_CSV.open(newline="", encoding="utf-8-sig") as source:
        return {
            normalize_kana_reading(row["declaredNormalizedReading"]): nfkc(row["zh"])
            for row in csv.DictReader(source)
            if nfkc(row.get("declaredNormalizedReading")) and nfkc(row.get("zh"))
        }


def word_text_rows(rows: list[dict[str, str]]) -> str:
    return "\n".join(
        "|".join(
            escape_pipe(row[field])
            for field in ["reading", "writing", "declaredNormalizedReading", "zh", "script"]
        )
        for row in rows
    )


def escape_pipe(value: str) -> str:
    return value.replace("|", "／").replace("\n", " ").strip()


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start) + len(end_marker)
    return text[:start] + replacement + text[end:]


def existing_context(word_data: str) -> tuple[list[dict[str, str]], set[str], dict[str, set[str]], set[str]]:
    n5_rows = parse_js_rows(slice_between(word_data, "  RAW_WORDS:", "  N4_BASE_WORD_ROWS:"))
    n4_base_rows = parse_js_rows(slice_between(word_data, "  N4_BASE_WORD_ROWS:", "  N4_EXTRA_WORD_ROWS_TEXT:"))
    n3_base_rows = parse_js_rows(slice_between(word_data, "  N3_BASE_WORD_ROWS:", "  N3_RESERVED_UPPER_LEVEL_READING_VALUES:"))

    n4_extra_rows = parse_pipe_rows(extract_word_text_property(word_data, "N4_EXTRA_WORD_ROWS_TEXT"))
    n4_csv_rows = parse_pipe_rows(extract_word_text_property(word_data, "N4_CSV_WORD_ROWS_TEXT"))
    n3_extra_rows = parse_pipe_rows(extract_word_text_property(word_data, "N3_EXTRA_WORD_ROWS_TEXT"))

    all_prior_rows = list(n5_rows) + list(n4_base_rows) + [
        ("", row["reading"], row["writing"], row["declaredNormalizedReading"], row["zh"], row["script"])
        for row in n4_extra_rows + n4_csv_rows
    ] + list(n3_base_rows) + [
        ("", row["reading"], row["writing"], row["declaredNormalizedReading"], row["zh"], row["script"])
        for row in n3_extra_rows
    ]

    existing_readings = {normalize_kana_reading(row[1] or row[3]) for row in all_prior_rows}
    writing_to_readings: dict[str, set[str]] = defaultdict(set)
    for row in all_prior_rows:
        reading = normalize_kana_reading(row[1] or row[3])
        writing = nfkc(row[2])
        if writing:
            writing_to_readings[writing].add(reading)

    reserved = {
        normalize_kana_reading(item.strip().strip('"'))
        for item in slice_between(
            word_data,
            "  N3_RESERVED_UPPER_LEVEL_READING_VALUES: [",
            "  N3_EXTRA_WORD_ROWS_TEXT:",
        ).replace("]", "").split(",")
        if item.strip().strip('"')
    }
    return n3_extra_rows, existing_readings, writing_to_readings, reserved


def clean_csv_rows(
    existing_readings: set[str],
    writing_to_readings: dict[str, set[str]],
    reserved_readings: set[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]], Counter[str]]:
    imported: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    reject_counts: Counter[str] = Counter()
    seen_imported_readings = set(existing_readings)
    zh_overrides = load_zh_overrides()

    def reject(row: dict[str, str], reason: str, reading: str, writing: str) -> None:
        reject_counts[reason] += 1
        rejected.append(
            {
                "reason": reason,
                "level": row.get("level", ""),
                "reading": reading,
                "writing": writing,
                "page": row.get("page", ""),
                "column": row.get("column", ""),
                "entry_no": row.get("entry_no", ""),
                "needs_review": row.get("needs_review", ""),
            }
        )

    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            reading = nfkc(row.get("reading", ""))
            writing = nfkc(row.get("writing", ""))

            if row.get("needs_review", "").strip():
                reject(row, "needs_review", reading, writing)
                continue
            if not reading:
                reject(row, "blank_reading", reading, writing)
                continue

            reading = READING_CORRECTIONS.get(reading, reading)
            normalized = normalize_kana_reading(reading)
            writing = WRITING_CORRECTIONS.get((reading, writing), writing)

            is_katakana = bool(KATAKANA_RE.fullmatch(reading))
            is_hiragana = bool(HIRAGANA_RE.fullmatch(reading))
            if not (is_katakana or is_hiragana):
                reject(row, "bad_reading_chars", reading, writing)
                continue
            if normalized in reserved_readings:
                reject(row, "reserved_upper_level_reading", reading, writing)
                continue
            if normalized in seen_imported_readings:
                reject(row, "duplicate_reading", reading, writing)
                continue

            if is_hiragana:
                if not writing:
                    writing = reading
                if writing in writing_to_readings and normalized not in writing_to_readings[writing]:
                    reject(row, "writing_exists_with_other_reading", reading, writing)
                    continue
                if re.search(r"[A-Za-z0-9!~【】\[\]{}<>]", writing):
                    reject(row, "bad_writing_chars", reading, writing)
                    continue
                if re.search(r"[ァ-ヶー]", writing):
                    reject(row, "mixed_katakana_writing", reading, writing)
                    continue
                display_writing = writing
                clue = writing
                script = "hiragana" if writing == reading else "kanji"
            else:
                display_writing = reading
                clue = writing if writing and ASCII_GLOSS_RE.fullmatch(writing) else reading
                script = "katakana"

            clue = zh_overrides.get(normalized, clue)

            imported.append(
                {
                    "reading": reading,
                    "writing": display_writing,
                    "declaredNormalizedReading": normalized,
                    "zh": clue,
                    "script": script,
                    "source_page": row.get("page", ""),
                    "source_column": row.get("column", ""),
                    "source_entry_no": row.get("entry_no", ""),
                    "source_writing": writing,
                }
            )
            seen_imported_readings.add(normalized)

    return imported, rejected, reject_counts


def merge_into_word_data(word_data: str, rows: list[dict[str, str]]) -> str:
    generated_block = f"{N3_BLOCK_START}\n\n{word_text_rows(rows)}\n{N3_BLOCK_END}"
    return replace_between(word_data, N3_BLOCK_START, N3_BLOCK_END, generated_block)


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    word_data = DATA_PATH.read_text(encoding="utf-8")
    existing_n3_rows, existing_readings, writing_to_readings, reserved_readings = existing_context(word_data)
    imported, rejected, reject_counts = clean_csv_rows(existing_readings, writing_to_readings, reserved_readings)
    merged_rows = existing_n3_rows + imported

    write_csv(
        CLEANED_CSV,
        imported,
        [
            "reading",
            "writing",
            "declaredNormalizedReading",
            "zh",
            "script",
            "source_page",
            "source_column",
            "source_entry_no",
            "source_writing",
        ],
    )
    write_csv(
        REJECTED_CSV,
        rejected,
        ["reason", "level", "reading", "writing", "page", "column", "entry_no", "needs_review"],
    )

    DATA_PATH.write_text(merge_into_word_data(word_data, merged_rows), encoding="utf-8")

    print(f"existing_n3_extra={len(existing_n3_rows)}")
    print(f"imported={len(imported)}")
    print(f"merged_n3_extra={len(merged_rows)}")
    print(f"rejected={len(rejected)}")
    for reason, count in sorted(reject_counts.items()):
        print(f"{reason}={count}")


if __name__ == "__main__":
    main()
