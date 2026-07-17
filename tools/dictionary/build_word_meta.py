#!/usr/bin/env python3
"""Build browser-ready learning metadata for Fat Shiba words."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CSV = PROJECT_ROOT / "tools" / "dictionary" / "word_meta.csv"
WORD_DATA_JS = PROJECT_ROOT / "web" / "data" / "word_data.js"
INDEX_HTML = PROJECT_ROOT / "web" / "index.html"
OUTPUT_JS = PROJECT_ROOT / "web" / "data" / "word_meta.js"

POS_LABELS = {
    "noun": "名詞",
    "verb": "動詞",
    "i_adjective": "い形容詞",
    "na_adjective": "な形容詞",
    "adverb": "副詞",
    "particle": "助詞",
    "expression": "慣用表現",
    "katakana": "外來語",
    "suru_noun": "する名詞",
    "counter": "助數詞",
    "prefix": "接頭語",
    "suffix": "接尾語",
}

VERB_CLASS_LABELS = {
    "ichidan": "一段動詞",
    "godan": "五段動詞",
    "godan_iku_exception": "五段動詞（行く例外）",
    "suru": "する動詞",
    "kuru": "来る",
    "irregular": "不規則動詞",
}

TRANSITIVITY_LABELS = {
    "transitive": "他動詞",
    "intransitive": "自動詞",
    "both": "自他兩用",
}

EXPECTED_FIELDS = [
    "id",
    "pos",
    "verb_class",
    "transitivity",
    "example_ja",
    "example_zh",
    "note",
]

JS_ROW_RE = re.compile(
    r'\["([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\]'
)

KANA_VOWELS = {
    **dict.fromkeys("あぁかがさざただなはばぱまやゃらわ", "a"),
    **dict.fromkeys("いぃきぎしじちぢにひびぴみり", "i"),
    **dict.fromkeys("うぅゔくぐすずつづぬふぶぷむゆゅる", "u"),
    **dict.fromkeys("えぇけげせぜてでねへべぺめれ", "e"),
    **dict.fromkeys("おぉこごそぞとどのほぼぽもよょろを", "o"),
}

GODAN_STEMS = {
    "う": ("い", "わ"),
    "く": ("き", "か"),
    "ぐ": ("ぎ", "が"),
    "す": ("し", "さ"),
    "つ": ("ち", "た"),
    "ぬ": ("に", "な"),
    "ぶ": ("び", "ば"),
    "む": ("み", "ま"),
    "る": ("り", "ら"),
}

GODAN_TE_TA = {
    "う": ("って", "った"),
    "つ": ("って", "った"),
    "る": ("って", "った"),
    "む": ("んで", "んだ"),
    "ぶ": ("んで", "んだ"),
    "ぬ": ("んで", "んだ"),
    "く": ("いて", "いた"),
    "ぐ": ("いで", "いだ"),
    "す": ("して", "した"),
}


def to_hiragana_kana(char: str) -> str:
    code = ord(char)
    if 0x30A1 <= code <= 0x30F6:
        return chr(code - 0x60)
    return char


def kana_vowel(kana: str) -> str:
    return KANA_VOWELS.get(to_hiragana_kana(kana), "")


def long_vowel_kana(previous_kana: str) -> str:
    return {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}.get(kana_vowel(previous_kana), "")


def normalize_kana_reading(value: str) -> str:
    output: list[str] = []
    for raw_char in value.strip():
        kana = to_hiragana_kana(raw_char)
        if kana == "ー":
            long_kana = long_vowel_kana(output[-1] if output else "")
            if long_kana:
                output.append(long_kana)
            continue
        output.append(kana)
    return "".join(output)


def row_dict(word_id: str, reading: str, writing: str, normalized: str, zh: str, script: str) -> dict[str, str]:
    return {
        "id": word_id,
        "reading": reading,
        "writing": writing,
        "normalizedReading": normalized,
        "zh": zh,
        "script": script,
    }


def explicit_word_rows(word_data: str) -> list[dict[str, str]]:
    return [row_dict(*match) for match in JS_ROW_RE.findall(word_data)]


def extract_pipe_text(word_data: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}:\s*`(.*?)`", word_data, flags=re.S)
    if not match:
        return ""
    return match.group(1)


def build_level_word_rows(
    prefix: str,
    start_number: int,
    rows_text: str,
    excluded_readings: set[str],
    limit: int | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen_readings = set(excluded_readings)

    for raw_row in rows_text.strip().splitlines():
        if limit is not None and len(rows) >= limit:
            break
        row = raw_row.strip()
        if not row:
            continue
        parts = [part.strip() for part in row.split("|")]
        if len(parts) != 5:
            raise ValueError(f"Invalid {prefix} word row: {row}")
        reading, writing, declared_normalized_reading, zh, script = parts
        normalized = normalize_kana_reading(reading or declared_normalized_reading)
        if normalized in seen_readings:
            continue
        seen_readings.add(normalized)
        rows.append(row_dict(
            f"{prefix}_{start_number + len(rows):04d}",
            reading,
            writing,
            normalized,
            zh,
            script,
        ))
    return rows


def reading_set(rows: list[dict[str, str]]) -> set[str]:
    return {normalize_kana_reading(row["reading"] or row["normalizedReading"]) for row in rows}


def load_word_index() -> dict[str, dict[str, str]]:
    word_data = WORD_DATA_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")
    explicit_rows = explicit_word_rows(word_data) + explicit_word_rows(index_html)
    rows_by_prefix = {
        prefix: [row for row in explicit_rows if row["id"].startswith(f"{prefix}_")]
        for prefix in ("n1", "n2", "n3", "n4", "n5")
    }

    n5_rows = rows_by_prefix["n5"]
    n4_base_rows = rows_by_prefix["n4"]
    n3_base_rows = rows_by_prefix["n3"]
    n2_base_rows = rows_by_prefix["n2"]
    n1_base_rows = rows_by_prefix["n1"]

    n5_readings = reading_set(n5_rows)
    n4_base_readings = reading_set(n4_base_rows)
    n4_extra_rows = build_level_word_rows(
        "n4",
        61,
        extract_pipe_text(word_data, "N4_EXTRA_WORD_ROWS_TEXT"),
        n5_readings | n4_base_readings,
        limit=540,
    )
    n4_csv_rows = build_level_word_rows(
        "n4",
        601,
        extract_pipe_text(word_data, "N4_CSV_WORD_ROWS_TEXT"),
        n5_readings | n4_base_readings | reading_set(n4_extra_rows),
    )
    n4_word_rows = [
        row for row in [*n4_base_rows, *n4_extra_rows, *n4_csv_rows]
        if normalize_kana_reading(row["reading"] or row["normalizedReading"]) not in n5_readings
        and not (row["normalizedReading"] == "いっぽう" and row["writing"] == "一方")
    ]

    n3_lower_readings = n5_readings | n4_base_readings | reading_set(n4_extra_rows)
    n3_base_readings = reading_set(n3_base_rows)
    reserved_n3_match = re.search(r"N3_RESERVED_UPPER_LEVEL_READING_VALUES:\s*\[(.*?)\]", word_data, flags=re.S)
    reserved_n3_readings = set(re.findall(r'"([^"]+)"', reserved_n3_match.group(1))) if reserved_n3_match else set()
    n3_extra_rows = build_level_word_rows(
        "n3",
        61,
        extract_pipe_text(word_data, "N3_EXTRA_WORD_ROWS_TEXT"),
        n3_lower_readings | n3_base_readings | {normalize_kana_reading(value) for value in reserved_n3_readings},
    )
    n3_word_rows = [
        row for row in [*n3_base_rows, *n3_extra_rows]
        if normalize_kana_reading(row["reading"] or row["normalizedReading"]) not in n3_lower_readings
    ]

    n2_lower_readings = reading_set([*n5_rows, *n4_word_rows, *n3_word_rows])
    n2_base_readings = reading_set(n2_base_rows)
    n2_extra_rows = build_level_word_rows(
        "n2",
        57,
        extract_pipe_text(word_data, "N2_EXTRA_WORD_ROWS_TEXT"),
        n2_lower_readings | n2_base_readings,
    )

    n1_lower_readings = reading_set([*n5_rows, *n4_word_rows, *n3_word_rows, *n2_base_rows, *n2_extra_rows])
    n1_base_readings = reading_set(n1_base_rows)
    n1_extra_rows = build_level_word_rows(
        "n1",
        51,
        extract_pipe_text(word_data, "N1_EXTRA_WORD_ROWS_TEXT"),
        n1_lower_readings | n1_base_readings,
    )

    words: dict[str, dict[str, str]] = {}
    for row in [
        *n5_rows,
        *n4_word_rows,
        *n3_word_rows,
        *n2_base_rows,
        *n2_extra_rows,
        *n1_base_rows,
        *n1_extra_rows,
    ]:
        words[row["id"]] = row
    return words


def without_last_kana(value: str) -> str:
    chars = list(value)
    if not chars:
        raise ValueError("Cannot conjugate a blank verb")
    return "".join(chars[:-1])


def verb_forms(dictionary_form: str, verb_class: str) -> dict[str, str]:
    if verb_class == "ichidan":
        if not dictionary_form.endswith("る"):
            raise ValueError(f"Ichidan verb must end with る: {dictionary_form}")
        stem = dictionary_form[:-1]
        return {
            "dictionary": dictionary_form,
            "masu": f"{stem}ます",
            "te": f"{stem}て",
            "ta": f"{stem}た",
            "nai": f"{stem}ない",
        }

    if verb_class == "kuru":
        return {
            "dictionary": dictionary_form,
            "masu": "来ます",
            "te": "来て",
            "ta": "来た",
            "nai": "来ない",
        }

    if verb_class == "suru":
        stem = dictionary_form[:-2] if dictionary_form.endswith("する") else ""
        return {
            "dictionary": dictionary_form,
            "masu": f"{stem}します",
            "te": f"{stem}して",
            "ta": f"{stem}した",
            "nai": f"{stem}しない",
        }

    if verb_class in {"godan", "godan_iku_exception"}:
        ending = dictionary_form[-1]
        if ending not in GODAN_STEMS:
            raise ValueError(f"Unsupported godan ending {ending}: {dictionary_form}")
        masu_ending, nai_ending = GODAN_STEMS[ending]
        te_ending, ta_ending = GODAN_TE_TA[ending]
        if verb_class == "godan_iku_exception":
            te_ending, ta_ending = "って", "った"
        stem = without_last_kana(dictionary_form)
        return {
            "dictionary": dictionary_form,
            "masu": f"{stem}{masu_ending}ます",
            "te": f"{stem}{te_ending}",
            "ta": f"{stem}{ta_ending}",
            "nai": f"{stem}{nai_ending}ない",
        }

    raise ValueError(f"Unsupported verb_class: {verb_class}")


def validate_headers(fieldnames: list[str] | None) -> None:
    if fieldnames != EXPECTED_FIELDS:
        raise ValueError(f"Expected CSV fields {EXPECTED_FIELDS}, got {fieldnames}")


def build_meta() -> dict[str, dict[str, object]]:
    words = load_word_index()
    seen_ids: set[str] = set()
    metadata: dict[str, dict[str, object]] = {}

    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        validate_headers(reader.fieldnames)
        for line_no, row in enumerate(reader, start=2):
            word_id = (row.get("id") or "").strip()
            pos = (row.get("pos") or "").strip()
            verb_class = (row.get("verb_class") or "").strip()
            transitivity = (row.get("transitivity") or "").strip()
            example_ja = (row.get("example_ja") or "").strip()
            example_zh = (row.get("example_zh") or "").strip()
            note = (row.get("note") or "").strip()

            if not word_id:
                raise ValueError(f"Line {line_no}: id is required")
            if word_id in seen_ids:
                raise ValueError(f"Line {line_no}: duplicate id {word_id}")
            if word_id not in words:
                raise ValueError(f"Line {line_no}: unknown word id {word_id}")
            if pos not in POS_LABELS:
                raise ValueError(f"Line {line_no}: unsupported pos {pos!r}")
            if bool(example_ja) != bool(example_zh):
                raise ValueError(f"Line {line_no}: example_ja and example_zh must be filled together")

            item: dict[str, object] = {
                "pos": pos,
                "posLabel": POS_LABELS[pos],
            }

            if transitivity:
                if transitivity not in TRANSITIVITY_LABELS:
                    raise ValueError(f"Line {line_no}: unsupported transitivity {transitivity!r}")
                item["transitivity"] = transitivity
                item["transitivityLabel"] = TRANSITIVITY_LABELS[transitivity]

            if pos == "verb":
                if verb_class not in VERB_CLASS_LABELS:
                    raise ValueError(f"Line {line_no}: unsupported verb_class {verb_class!r}")
                dictionary_form = words[word_id]["writing"] or words[word_id]["reading"]
                item["verbClass"] = verb_class
                item["verbClassLabel"] = VERB_CLASS_LABELS[verb_class]
                item["forms"] = verb_forms(dictionary_form, verb_class)
            elif verb_class:
                raise ValueError(f"Line {line_no}: non-verb rows cannot set verb_class")

            if example_ja:
                item["examples"] = [{"ja": example_ja, "zh": example_zh}]
            if note:
                item["note"] = note

            seen_ids.add(word_id)
            metadata[word_id] = item

    return metadata


def main() -> None:
    metadata = build_meta()
    payload = json.dumps(metadata, ensure_ascii=False, indent=2)
    OUTPUT_JS.write_text(
        "// Generated by tools/dictionary/build_word_meta.py. Do not edit by hand.\n"
        f"window.FAT_SHIBA_WORD_META = {payload};\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT_JS.relative_to(PROJECT_ROOT)} ({len(metadata)} entries)")


if __name__ == "__main__":
    main()
