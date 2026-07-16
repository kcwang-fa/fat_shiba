#!/usr/bin/env python3
"""Clean the corrected N4 CSV and merge high-confidence rows into word data.

The source CSV was produced from OCR, so this script intentionally imports
only rows that are safe for the game:

- no manual-review flags
- kana-only readings
- no duplicate reading already present in N5 or the original N4 list
- no likely OCR reading when the same writing already exists with another
  reading in N5/original N4

Chinese meanings are stored in dictionary/jlpt_n4_zh_overrides.csv so the
OCR cleanup rules and translation data can be maintained separately.
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
SOURCE_CSV = TOOL_ROOT / "dictionary" / "jlpt_n4_wordlist_corrected.csv"
ZH_OVERRIDES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n4_zh_overrides.csv"
CLEANED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n4_wordlist_cleaned_for_game.csv"
REJECTED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n4_wordlist_rejected_for_game.csv"

CSV_BLOCK_START = "  N4_CSV_WORD_ROWS_TEXT: `"
CSV_BLOCK_END = "`,\n  N3_BASE_WORD_ROWS"


HIRAGANA_RE = re.compile(r"^[ぁ-んー]+$")
KATAKANA_RE = re.compile(r"^[ァ-ヶー]+$")
ASCII_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z .+\-]*$")
JS_ROW_RE = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)


READING_CORRECTIONS = {
    "いつっしょうけんめい": "いっしょうけんめい",
    "えんりよょ": "えんりょ",
    "くぴび": "くび",
    "であい": "ぐあい",
    "じゅんぴ": "じゅんび",
    "さんぎょよう": "さんぎょう",
    "しんばい": "しんぱい",
    "ぴっくり": "びっくり",
    "ぶんぼう": "ぶんぽう",
    "てんぶ": "てんぷ",
    "こうきようりようきん": "こうきょうりょうきん",
}

WRITING_CORRECTIONS = {
    ("いってまいります", "行っ 参ります"): "行って参ります",
    ("かっこう", "格好・情好"): "格好",
    ("くび", "首"): "首",
    ("ゆうはん", "タ飯"): "夕飯",
    ("えんかい", "富会"): "宴会",
    ("まんが", "温画"): "漫画",
    ("ちゅうしゃいはん", "駐違反"): "駐車違反",
    ("けいざいがく", "和経済学"): "経済学",
    ("こうき", "後其"): "後期",
    ("てんぷ", "添付"): "添付",
    ("ベル", "bel"): "bell",
    ("アクセサリー", "accessary"): "accessory",
    ("インストール", "instal"): "install",
    ("メールアドレス", "mail ddress"): "mail address",
}

MANUAL_SKIP_READINGS = {
    "たべべほうだい",
    "きゅうぷれーき",
    "とくぺつ",
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


def original_word_rows(word_data: str) -> tuple[list[tuple[str, str, str, str, str, str]], set[str], dict[str, set[str]]]:
    n5_rows = parse_js_rows(slice_between(word_data, "  RAW_WORDS:", "  N4_BASE_WORD_ROWS:"))
    n5_readings = {normalize_kana_reading(row[1] or row[3]) for row in n5_rows}

    n4_base_rows = parse_js_rows(slice_between(word_data, "  N4_BASE_WORD_ROWS:", "  N4_EXTRA_WORD_ROWS_TEXT:"))
    n4_base_readings = {normalize_kana_reading(row[1] or row[3]) for row in n4_base_rows}

    extra_text = extract_word_text_property(word_data, "N4_EXTRA_WORD_ROWS_TEXT")

    seen_readings = set(n5_readings) | set(n4_base_readings)
    n4_extra_rows: list[tuple[str, str, str, str, str, str]] = []
    for line in extra_text.strip().splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 5:
            raise ValueError(f"Invalid N4 extra row: {line}")
        reading, writing, declared, zh, script = parts
        normalized = normalize_kana_reading(reading or declared)
        if normalized in seen_readings:
            continue
        seen_readings.add(normalized)
        n4_extra_rows.append(("", reading, writing, normalized, zh, script))
        if len(n4_extra_rows) >= 540:
            break

    original_rows = list(n5_rows) + list(n4_base_rows) + n4_extra_rows
    writing_to_readings: dict[str, set[str]] = defaultdict(set)
    for row in original_rows:
        reading = normalize_kana_reading(row[1] or row[3])
        writing = nfkc(row[2])
        if writing:
            writing_to_readings[writing].add(reading)

    original_n4_readings = {
        normalize_kana_reading(row[1] or row[3])
        for row in n4_base_rows + n4_extra_rows
        if normalize_kana_reading(row[1] or row[3]) not in n5_readings
    }
    original_n4_readings.discard("いっぽう")

    return original_rows, n5_readings | original_n4_readings, writing_to_readings


def load_zh_overrides() -> dict[str, str]:
    if not ZH_OVERRIDES_CSV.exists():
        return {}

    with ZH_OVERRIDES_CSV.open(newline="", encoding="utf-8-sig") as source:
        return {
            normalize_kana_reading(row["declaredNormalizedReading"]): nfkc(row["zh"])
            for row in csv.DictReader(source)
            if nfkc(row.get("declaredNormalizedReading")) and nfkc(row.get("zh"))
        }


def clean_csv_rows(existing_readings: set[str], writing_to_readings: dict[str, set[str]]) -> tuple[list[dict[str, str]], list[dict[str, str]], Counter[str]]:
    imported: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    reject_counts: Counter[str] = Counter()
    seen_imported_readings = set(existing_readings)
    zh_overrides = load_zh_overrides()

    def reject(row: dict[str, str], reason: str, reading: str, writing: str) -> None:
        reject_counts[reason] += 1
        rejected.append({
            "reason": reason,
            "level": row.get("level", ""),
            "reading": reading,
            "writing": writing,
            "page": row.get("page", ""),
            "column": row.get("column", ""),
            "entry_no": row.get("entry_no", ""),
            "needs_review": row.get("needs_review", ""),
        })

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
            if normalized in MANUAL_SKIP_READINGS:
                reject(row, "manual_skip_reading", reading, writing)
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

            imported.append({
                "reading": reading,
                "writing": display_writing,
                "declaredNormalizedReading": normalized,
                "zh": clue,
                "script": script,
                "source_page": row.get("page", ""),
                "source_column": row.get("column", ""),
                "source_entry_no": row.get("entry_no", ""),
                "source_writing": writing,
            })
            seen_imported_readings.add(normalized)

    return imported, rejected, reject_counts


def escape_pipe(value: str) -> str:
    return value.replace("|", "／").replace("\n", " ").strip()


def word_rows_text(rows: list[dict[str, str]]) -> str:
    return "\n".join(
        "|".join(
            escape_pipe(row[field])
            for field in ["reading", "writing", "declaredNormalizedReading", "zh", "script"]
        )
        for row in rows
    )


def extract_word_text_property(word_data: str, name: str) -> str:
    marker = f"  {name}: `"
    start = word_data.index(marker) + len(marker)
    end = word_data.index("`", start)
    return word_data[start:end]


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        return text
    end = text.find(end_marker, start)
    if end == -1:
        raise ValueError(f"Found {start_marker!r} without matching end marker")
    end += len(end_marker)
    return text[:start] + replacement + text[end:]


def merge_into_word_data(word_data: str, rows: list[dict[str, str]]) -> str:
    generated_block = f"{CSV_BLOCK_START}\n{word_rows_text(rows)}\n{CSV_BLOCK_END}"
    return replace_between(word_data, CSV_BLOCK_START, CSV_BLOCK_END, generated_block)


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    word_data = DATA_PATH.read_text(encoding="utf-8")
    _, existing_readings, writing_to_readings = original_word_rows(word_data)
    imported, rejected, reject_counts = clean_csv_rows(existing_readings, writing_to_readings)

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

    DATA_PATH.write_text(merge_into_word_data(word_data, imported), encoding="utf-8")

    print(f"imported={len(imported)}")
    print(f"rejected={len(rejected)}")
    for reason, count in sorted(reject_counts.items()):
        print(f"{reason}={count}")


if __name__ == "__main__":
    main()
