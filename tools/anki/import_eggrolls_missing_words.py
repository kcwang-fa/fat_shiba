#!/usr/bin/env python3
"""Import missing Eggrolls Anki words into Fat Shiba word data.

The import keeps existing hand-curated word rows intact. New words are written
to separate EGGROLLS_N*_WORD_ROWS_TEXT blocks so generated IDs for existing
rows do not shift.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORD_DATA_PATH = PROJECT_ROOT / "web" / "data" / "word_data.js"
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"
NOTES_TSV = PROJECT_ROOT / "outputs" / "eggrolls_JLPT10k_v3_5_apkg_parse" / "notes.tsv"
AUDIT_DIR = PROJECT_ROOT / "outputs" / "eggrolls_JLPT10k_v3_5_word_import"

LEVELS = ["N5", "N4", "N3", "N2", "N1"]
EGGROLLS_BLOCKS = {
    "N5": "EGGROLLS_N5_WORD_ROWS_TEXT",
    "N4": "EGGROLLS_N4_WORD_ROWS_TEXT",
    "N3": "EGGROLLS_N3_WORD_ROWS_TEXT",
    "N2": "EGGROLLS_N2_WORD_ROWS_TEXT",
    "N1": "EGGROLLS_N1_WORD_ROWS_TEXT",
}

JS_ROW_RE = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)
HIRAGANA_RE = re.compile(r"^[ぁ-んー]+$")
KATAKANA_RE = re.compile(r"^[ァ-ヶー]+$")
KANA_MIX_RE = re.compile(r"^[ぁ-んァ-ヶー]+$")
HTML_TAG_RE = re.compile(r"<[^>]+>")
FURIGANA_MARKUP_RE = re.compile(r"\[[^\]]+\]")


@dataclass(frozen=True)
class WordRow:
    level: str
    reading: str
    writing: str
    declared: str
    zh: str
    script: str
    source_note_id: str = ""
    source_order: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return normalize_kana_reading(self.reading or self.declared), nfkc(self.writing)

    def pipe_row(self) -> str:
        return "|".join(
            escape_pipe(value)
            for value in [self.reading, self.writing, self.declared, self.zh, self.script]
        )


def nfkc(value: str | None) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip())


def strip_html(value: str | None) -> str:
    return HTML_TAG_RE.sub("", nfkc(value)).replace("&nbsp;", " ").strip()


def clean_writing(value: str | None) -> str:
    text = strip_html(value)
    text = FURIGANA_MARKUP_RE.sub("", text)
    return text.replace(" ", "").replace("　", "").strip()


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
            long_vowel = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}.get(
                kana_vowel(output[-1]) if output else ""
            )
            if long_vowel:
                output.append(long_vowel)
            continue
        output.append(kana)
    return "".join(output)


def escape_pipe(value: str) -> str:
    return nfkc(value).replace("|", "／").replace("\n", " ").replace("\r", " ").strip()


def slice_between(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def extract_text_property(text: str, name: str) -> str:
    marker = f"  {name}: `"
    if marker not in text:
        return ""
    start = text.index(marker) + len(marker)
    end = text.index("`", start)
    return text[start:end]


def parse_js_rows(block: str, level: str) -> list[WordRow]:
    rows: list[WordRow] = []
    for _, reading, writing, declared, zh, script in JS_ROW_RE.findall(block):
        rows.append(
            WordRow(
                level=level,
                reading=nfkc(reading),
                writing=nfkc(writing),
                declared=normalize_kana_reading(declared or reading),
                zh=nfkc(zh),
                script=nfkc(script),
            )
        )
    return rows


def parse_pipe_rows(text: str, level: str) -> list[WordRow]:
    rows: list[WordRow] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 5:
            continue
        reading, writing, declared, zh, script = parts
        rows.append(
            WordRow(
                level=level,
                reading=nfkc(reading),
                writing=nfkc(writing),
                declared=normalize_kana_reading(declared or reading),
                zh=nfkc(zh),
                script=nfkc(script),
            )
        )
    return rows


def existing_word_rows(word_data: str, index_html: str, include_eggrolls: bool = False) -> list[WordRow]:
    rows: list[WordRow] = []
    rows += parse_js_rows(slice_between(word_data, "  RAW_WORDS:", "  N4_BASE_WORD_ROWS:"), "N5")
    rows += parse_js_rows(slice_between(word_data, "  N4_BASE_WORD_ROWS:", "  N4_EXTRA_WORD_ROWS_TEXT:"), "N4")
    rows += parse_pipe_rows(extract_text_property(word_data, "N4_EXTRA_WORD_ROWS_TEXT"), "N4")
    rows += parse_pipe_rows(extract_text_property(word_data, "N4_CSV_WORD_ROWS_TEXT"), "N4")
    rows += parse_js_rows(
        slice_between(word_data, "  N3_BASE_WORD_ROWS:", "  N3_RESERVED_UPPER_LEVEL_READING_VALUES:"),
        "N3",
    )
    rows += parse_pipe_rows(extract_text_property(word_data, "N3_EXTRA_WORD_ROWS_TEXT"), "N3")
    rows += parse_js_rows(slice_between(index_html, "      const N2_BASE_WORD_ROWS = [", "      ];"), "N2")
    rows += parse_pipe_rows(extract_text_property(word_data, "N2_EXTRA_WORD_ROWS_TEXT"), "N2")
    rows += parse_js_rows(slice_between(word_data, "  N1_BASE_WORD_ROWS:", "  N1_EXTRA_WORD_ROWS_TEXT:"), "N1")
    rows += parse_pipe_rows(extract_text_property(word_data, "N1_EXTRA_WORD_ROWS_TEXT"), "N1")

    if include_eggrolls:
        for level, block_name in EGGROLLS_BLOCKS.items():
            rows += parse_pipe_rows(extract_text_property(word_data, block_name), level)

    return rows


def level_from_anki(row: dict[str, str]) -> str:
    text = f"{row.get('deck_name', '')} {row.get('tags', '')}"
    for level in LEVELS[::-1]:
        if level in text:
            return level
    return ""


def choose_anki_reading(row: dict[str, str]) -> tuple[str, str]:
    furigana = nfkc(row.get("VocabFurigana"))
    vocab = nfkc(row.get("VocabKanji"))
    if KANA_MIX_RE.fullmatch(furigana):
        return furigana, "furigana_kana"
    if KATAKANA_RE.fullmatch(vocab):
        return vocab, "katakana_vocab"
    return "", "non_kana_reading"


def script_for(reading: str, writing: str) -> str:
    if KATAKANA_RE.fullmatch(reading) and reading == writing:
        return "katakana"
    if HIRAGANA_RE.fullmatch(writing):
        return "hiragana"
    return "kanji"


def order_key(row: WordRow) -> tuple[float, str, str]:
    try:
        order = float(row.source_order)
    except ValueError:
        order = float("inf")
    return order, row.declared, row.writing


def load_anki_candidates(existing_keys: set[tuple[str, str]]) -> tuple[dict[str, list[WordRow]], list[dict[str, str]], list[dict[str, str]]]:
    imported: dict[str, list[WordRow]] = defaultdict(list)
    skipped: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    seen_keys = set(existing_keys)

    with NOTES_TSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            level = level_from_anki(row)
            reading, reading_source = choose_anki_reading(row)
            writing = clean_writing(row.get("VocabKanji"))
            zh = strip_html(row.get("VocabDefTC"))
            note_id = nfkc(row.get("NoteID"))
            source_order = nfkc(row.get("Order"))

            base_audit = {
                "level": level,
                "reading": reading,
                "writing": writing,
                "zh": zh,
                "note_id": note_id,
                "order": source_order,
                "reading_source": reading_source,
            }

            if not level:
                rejected.append({**base_audit, "reason": "missing_level"})
                continue
            if not reading:
                rejected.append({**base_audit, "reason": "non_playable_reading"})
                continue
            if not writing:
                rejected.append({**base_audit, "reason": "missing_writing"})
                continue
            if not zh:
                rejected.append({**base_audit, "reason": "missing_zh"})
                continue

            declared = normalize_kana_reading(reading)
            candidate = WordRow(
                level=level,
                reading=reading,
                writing=writing,
                declared=declared,
                zh=zh,
                script=script_for(reading, writing),
                source_note_id=note_id,
                source_order=source_order,
            )

            if candidate.key in existing_keys:
                skipped.append({**base_audit, "reason": "already_in_word_data"})
                continue
            if candidate.key in seen_keys:
                skipped.append({**base_audit, "reason": "duplicate_in_anki_import"})
                continue

            seen_keys.add(candidate.key)
            imported[level].append(candidate)

    for rows in imported.values():
        rows.sort(key=order_key)

    return imported, skipped, rejected


def render_text_block(rows: list[WordRow]) -> str:
    return "\n".join(row.pipe_row() for row in rows)


def upsert_text_property(word_data: str, name: str, body: str) -> str:
    marker = f"  {name}: `"
    replacement_with_comma = f"  {name}: `\n{body}\n`,\n"
    replacement_without_comma = f"  {name}: `\n{body}\n`"
    if marker in word_data:
        start = word_data.index(marker)
        body_start = start + len(marker)
        tick_end = word_data.index("\n`", body_start) + len("\n`")
        if word_data.startswith(",", tick_end):
            end = tick_end + 1
            if word_data.startswith("\n", end):
                end += 1
            return word_data[:start] + replacement_with_comma + word_data[end:]
        return word_data[:start] + replacement_without_comma + word_data[tick_end:]

    insert_at = word_data.rindex("\n};")
    prefix = "" if word_data[:insert_at].rstrip().endswith(",") else ","
    return word_data[:insert_at] + prefix + "\n" + replacement_without_comma + word_data[insert_at:]


def update_word_data(word_data: str, imported: dict[str, list[WordRow]]) -> str:
    updated = word_data
    for level in LEVELS:
        updated = upsert_text_property(updated, EGGROLLS_BLOCKS[level], render_text_block(imported.get(level, [])))
    return updated


def write_audit(imported: dict[str, list[WordRow]], skipped: list[dict[str, str]], rejected: list[dict[str, str]]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    imported_path = AUDIT_DIR / "eggrolls_imported_words.csv"
    with imported_path.open("w", newline="", encoding="utf-8-sig") as target:
        fields = ["level", "reading", "writing", "declared", "zh", "script", "note_id", "order"]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for level in LEVELS:
            for row in imported.get(level, []):
                writer.writerow(
                    {
                        "level": row.level,
                        "reading": row.reading,
                        "writing": row.writing,
                        "declared": row.declared,
                        "zh": row.zh,
                        "script": row.script,
                        "note_id": row.source_note_id,
                        "order": row.source_order,
                    }
                )

    for filename, rows in [
        ("eggrolls_skipped_words.csv", skipped),
        ("eggrolls_rejected_words.csv", rejected),
    ]:
        path = AUDIT_DIR / filename
        fieldnames = ["reason", "level", "reading", "writing", "zh", "note_id", "order", "reading_source"]
        with path.open("w", newline="", encoding="utf-8-sig") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    word_data = WORD_DATA_PATH.read_text(encoding="utf-8")
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    existing_rows = existing_word_rows(word_data, index_html)
    existing_keys = {row.key for row in existing_rows}

    imported, skipped, rejected = load_anki_candidates(existing_keys)
    updated_word_data = update_word_data(word_data, imported)
    WORD_DATA_PATH.write_text(updated_word_data, encoding="utf-8")
    write_audit(imported, skipped, rejected)

    imported_counts = {level: len(imported.get(level, [])) for level in LEVELS}
    skipped_counts = Counter(row["reason"] for row in skipped)
    rejected_counts = Counter(row["reason"] for row in rejected)
    print("existing_words", len(existing_rows))
    print("imported", imported_counts, "total", sum(imported_counts.values()))
    print("skipped", dict(skipped_counts), "total", len(skipped))
    print("rejected", dict(rejected_counts), "total", len(rejected))
    print("audit_dir", AUDIT_DIR)


if __name__ == "__main__":
    main()
