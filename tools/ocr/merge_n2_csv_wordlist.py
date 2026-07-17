#!/usr/bin/env python3
"""Merge reviewed N2 OCR rows into the game word data.

This keeps the existing hand-authored N2 list, imports only conservative OCR
rows, derives Chinese glosses from OCR context, and writes review artifacts so
the import can be audited and rerun.
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
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"
SOURCE_CSV = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_corrected.csv"
CANDIDATES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_candidates.csv"
CLEANED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_cleaned_for_game.csv"
REJECTED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_rejected_for_game.csv"
AUDIT_CSV = TOOL_ROOT / "dictionary" / "jlpt_n2_wordlist_import_audit.csv"

CSV_BLOCK_START = "  N2_EXTRA_WORD_ROWS_TEXT: `"
CSV_BLOCK_END = "`,\n  N1_BASE_WORD_ROWS"


JS_ROW_RE = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)
HIRAGANA_RE = re.compile(r"^[ぁ-んー]+$")
KATAKANA_RE = re.compile(r"^[ァ-ヶー]+$")
CJK_RE = re.compile(r"[一-龯々〆]")
BAD_READING_RE = re.compile(r"[^ぁ-んァ-ヶー]")
BAD_GAME_TEXT_RE = re.compile(r"[|`]")
ASCII_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z .+\-]*$")
LATIN_NOISE_RE = re.compile(r"[A-Za-z]{2,}")


READING_CORRECTIONS = {
    "ざっおん": "ざつおん",
    "ひようか": "ひょうか",
    "ひようし": "ひょうし",
    "ひゃやっかじてん": "ひゃっかじてん",
    "でんりょよく": "でんりょく",
    "じゅぎょうりょよう": "じゅぎょうりょう",
    "どうきよょ": "どうきょ",
    "にトゅぁうよく": "にゅうよく",
    "じこくひよう": "じこくひょう",
}

WRITING_CORRECTIONS = {
    ("いよいよ", "孔々"): "愈々",
    ("ざつおん", "雑音"): "雑音",
    ("ひねる", "披る"): "捻る",
    ("まっき", "未期"): "末期",
    ("すきま", "隙間"): "隙間",
    ("かいてき", "似適"): "快適",
    ("きゃしゃ", "華著"): "華奢",
    ("さく", "机"): "柵",
    ("ブザー", "buzzer"): "ブザー",
    ("しっぴつ", "封筆"): "執筆",
    ("はさむ", "挟ね"): "挟む",
    ("すくう", "拘う"): "掬う",
}

MANUAL_SKIP_READINGS = {
    "站也!",
    "譯天亮・1",
    "期間期限i",
    "護(walw<",
    "おがと",
    "扎儿大",
    "圭杞(a",
}

EXISTING_ZH_CORRECTIONS = {
    "ばい": "倍數、倍",
    "なぞ": "謎、謎語",
}

ZH_CORRECTIONS = {
    "おどりでる": "躍出、突然出現",
    "きわめる": "鑽研到底、達到極限",
    "くっつける": "黏上、貼上",
    "シャープペンシル": "自動鉛筆",
    "しゃあぷぺんしる": "自動鉛筆",
    "レンズ": "鏡片、鏡頭",
    "れんず": "鏡片、鏡頭",
    "つまずく": "絆倒、受挫",
    "うばう": "奪取、剝奪",
    "ばっする": "處罰、責罰",
    "ためらう": "猶豫、遲疑",
    "とがる": "尖銳、神經緊張",
    "なす": "做、為",
    "くるしむ": "痛苦、難受",
    "きみがわるい": "毛骨悚然、令人不快",
    "ひねる": "扭、擰",
    "ごくろうさま": "辛苦了",
    "ぜひとも": "一定、無論如何",
    "どういたしまして": "不客氣",
    "たてがき": "直寫、縱書",
    "はさむ": "夾住、插入",
    "ざつおん": "雜音、噪音",
    "じゅわき": "聽筒",
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


def extract_word_text_property(word_data: str, name: str, end_marker: str) -> str:
    marker = f"  {name}: `"
    start = word_data.index(marker) + len(marker)
    end = word_data.index(end_marker, start)
    return word_data[start:end]


def parse_pipe_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 5:
            rows.append({"invalid": line})
            continue
        reading, writing, normalized, zh, script = parts
        rows.append({
            "reading": reading,
            "writing": writing,
            "declaredNormalizedReading": normalized,
            "zh": zh,
            "script": script,
        })
    return rows


def existing_readings(word_data: str, index_html: str) -> tuple[set[str], list[dict[str, str]]]:
    blocks: list[tuple[str, str]] = [
        ("RAW_WORDS", slice_between(word_data, "  RAW_WORDS:", "  N4_BASE_WORD_ROWS:")),
        ("N4_BASE_WORD_ROWS", slice_between(word_data, "  N4_BASE_WORD_ROWS:", "  N4_EXTRA_WORD_ROWS_TEXT:")),
        ("N3_BASE_WORD_ROWS", slice_between(word_data, "  N3_BASE_WORD_ROWS:", "  N3_RESERVED_UPPER_LEVEL_READING_VALUES:")),
        ("N2_BASE_WORD_ROWS", slice_between(index_html, "      const N2_BASE_WORD_ROWS = [", "      ];\n\n      const N2_LOWER_LEVEL_READINGS")),
    ]
    readings: set[str] = set()
    for _, block in blocks:
        for row in parse_js_rows(block):
            readings.add(normalize_kana_reading(row[1] or row[3]))

    for name, end_marker in [
        ("N4_EXTRA_WORD_ROWS_TEXT", "`,\n  N4_CSV_WORD_ROWS_TEXT"),
        ("N4_CSV_WORD_ROWS_TEXT", "`,\n  N3_BASE_WORD_ROWS"),
        ("N3_EXTRA_WORD_ROWS_TEXT", "`,\n  N2_EXTRA_WORD_ROWS_TEXT"),
    ]:
        for row in parse_pipe_rows(extract_word_text_property(word_data, name, end_marker)):
            if "invalid" not in row:
                readings.add(normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"]))

    n2_existing = [
        row for row in parse_pipe_rows(extract_word_text_property(word_data, "N2_EXTRA_WORD_ROWS_TEXT", CSV_BLOCK_END))
        if "invalid" not in row
    ]
    return readings, n2_existing


def load_candidate_contexts() -> tuple[dict[tuple[str, str, str, str], str], dict[tuple[str, str, str], str]]:
    contexts: dict[tuple[str, str, str, str], str] = {}
    fallback_contexts: dict[tuple[str, str, str], str] = {}
    if not CANDIDATES_CSV.exists():
        return contexts, fallback_contexts
    with CANDIDATES_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            key = (
                nfkc(row.get("reading")),
                nfkc(row.get("writing")),
                nfkc(row.get("page")),
                nfkc(row.get("column")),
            )
            context = nfkc(row.get("ocr_context"))
            contexts.setdefault(key, context)
            fallback_contexts.setdefault(
                (nfkc(row.get("reading")), nfkc(row.get("page")), nfkc(row.get("column"))),
                context,
            )
    return contexts, fallback_contexts


def clean_gloss_segment(value: str) -> str:
    value = nfkc(value)
    value = value.replace("・", "、")
    value = re.sub(r"N[12345]", "", value)
    value = re.split(r"[。.!?！？]", value, maxsplit=1)[0]
    value = re.sub(r"^[^一-龯々〆]+", "", value)
    value = re.sub(r"^(名|副|形動|感|接|代|連体|漢造|自|他|五|上一|下一|サ|俗|敬|謙|文)[)）・、:;\s]+", "", value)
    value = re.sub(r"[ぁ-んァ-ヶー]+", "", value)
    value = re.sub(r"[()\[\]{}<>「」『』【】|/@①-⑳0-9A-Za-z~^_+=#$%&*]+", " ", value)
    value = re.sub(r"[、,，;；:：\s]+", "、", value)
    value = value.strip("、-—'\"“”")
    parts = [part for part in value.split("、") if part and len(part) <= 12]
    while len(parts) > 1 and len(parts[0]) == 1:
        parts.pop(0)
    value = "、".join(parts)
    if len(value) > 48:
        value = value[:48].rstrip("、") + "…"
    return value


def extract_zh(context: str, writing: str) -> str:
    segments = [segment.strip() for segment in nfkc(context).split(" / ") if segment.strip()]
    for segment in segments[1:4]:
        gloss = clean_gloss_segment(segment)
        if CJK_RE.search(gloss) and len(gloss) >= 2 and not LATIN_NOISE_RE.search(gloss):
            return gloss
    if writing and CJK_RE.search(writing) and not ASCII_GLOSS_RE.fullmatch(writing):
        return writing
    return ""


def infer_script(reading: str, writing: str) -> str:
    if KATAKANA_RE.fullmatch(reading):
        return "katakana"
    return "hiragana" if writing == reading else "kanji"


def escape_pipe(value: str) -> str:
    return value.replace("|", "／").replace("\n", " ").strip()


def word_rows_text(rows: list[dict[str, str]]) -> str:
    return "\n".join(
        "|".join(escape_pipe(row[field]) for field in ["reading", "writing", "declaredNormalizedReading", "zh", "script"])
        for row in rows
    )


def replace_n2_block(word_data: str, rows: list[dict[str, str]]) -> str:
    replacement = f"{CSV_BLOCK_START}\n{word_rows_text(rows)}\n{CSV_BLOCK_END}"
    start = word_data.index(CSV_BLOCK_START)
    end = word_data.index(CSV_BLOCK_END, start) + len(CSV_BLOCK_END)
    return word_data[:start] + replacement + word_data[end:]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def merge_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], Counter[str]]:
    word_data = DATA_PATH.read_text(encoding="utf-8")
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    lower_and_base_readings, existing_n2_rows = existing_readings(word_data, index_html)
    source_readings_for_cleanup: set[str] = set()
    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            reading = READING_CORRECTIONS.get(nfkc(row.get("reading")), nfkc(row.get("reading")))
            if reading:
                source_readings_for_cleanup.add(normalize_kana_reading(reading))
    existing_n2_rows = [
        row for row in existing_n2_rows
        if not (
            normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"]) in source_readings_for_cleanup
            and (not CJK_RE.search(row["zh"]) or len(row["zh"]) == 1)
        )
    ]
    for row in existing_n2_rows:
        normalized = normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"])
        if normalized in EXISTING_ZH_CORRECTIONS:
            row["zh"] = EXISTING_ZH_CORRECTIONS[normalized]
        if normalized in ZH_CORRECTIONS:
            row["zh"] = ZH_CORRECTIONS[normalized]
    existing_n2_readings = {
        normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"])
        for row in existing_n2_rows
    }
    appended_readings: set[str] = set()
    contexts, fallback_contexts = load_candidate_contexts()
    imported: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    reject_counts: Counter[str] = Counter()

    def reject(row: dict[str, str], reason: str, reading: str, writing: str, zh: str = "") -> None:
        reject_counts[reason] += 1
        rejected.append({
            "reason": reason,
            "level": row.get("level", ""),
            "reading": reading,
            "writing": writing,
            "zh": zh,
            "page": row.get("page", ""),
            "column": row.get("column", ""),
            "entry_no": row.get("entry_no", ""),
            "needs_review": row.get("needs_review", ""),
            "review_reason": row.get("review_reason", ""),
        })

    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            reading = nfkc(row.get("reading"))
            writing = nfkc(row.get("writing"))
            reading = READING_CORRECTIONS.get(reading, reading)
            writing = WRITING_CORRECTIONS.get((reading, writing), writing)
            normalized = normalize_kana_reading(reading)

            if row.get("needs_review", "").strip():
                reject(row, "needs_review", reading, writing)
                continue
            if not reading:
                reject(row, "blank_reading", reading, writing)
                continue
            if reading in MANUAL_SKIP_READINGS:
                reject(row, "manual_skip_reading", reading, writing)
                continue
            if BAD_READING_RE.search(reading):
                reject(row, "bad_reading_chars", reading, writing)
                continue
            if normalized in lower_and_base_readings:
                reject(row, "duplicate_reading", reading, writing)
                continue
            if not writing:
                writing = reading
            if BAD_GAME_TEXT_RE.search(reading) or BAD_GAME_TEXT_RE.search(writing):
                reject(row, "bad_game_text", reading, writing)
                continue

            context = contexts.get(
                (nfkc(row.get("reading")), nfkc(row.get("writing")), nfkc(row.get("page")), nfkc(row.get("column"))),
                "",
            )
            if not context:
                context = fallback_contexts.get((nfkc(row.get("reading")), nfkc(row.get("page")), nfkc(row.get("column"))), "")
            zh = ZH_CORRECTIONS.get(normalized) or extract_zh(context, writing)
            if not zh:
                reject(row, "blank_zh", reading, writing)
                continue
            if len(zh) == 1:
                reject(row, "too_short_zh", reading, writing, zh)
                continue
            if BAD_GAME_TEXT_RE.search(zh):
                reject(row, "bad_zh_chars", reading, writing, zh)
                continue

            script = infer_script(reading, writing)
            display_writing = reading if script == "katakana" else writing
            imported.append({
                "reading": reading,
                "writing": display_writing,
                "declaredNormalizedReading": normalized,
                "zh": zh,
                "script": script,
                "source_page": row.get("page", ""),
                "source_column": row.get("column", ""),
                "source_entry_no": row.get("entry_no", ""),
                "source_writing": writing,
            })
            if normalized in existing_n2_readings:
                continue
            if normalized in appended_readings:
                reject(row, "duplicate_source_reading", reading, writing, zh)
                continue
            appended_readings.add(normalized)

    merged_rows = existing_n2_rows + [
        {field: row[field] for field in ["reading", "writing", "declaredNormalizedReading", "zh", "script"]}
        for row in imported
        if row["declaredNormalizedReading"] in appended_readings
    ]
    DATA_PATH.write_text(replace_n2_block(word_data, merged_rows), encoding="utf-8")
    return imported, rejected, merged_rows, reject_counts


def audit_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    audits: list[dict[str, str]] = []
    reading_counts = Counter(row["declaredNormalizedReading"] for row in rows)
    for index, row in enumerate(rows, start=1):
        reasons: list[str] = []
        if reading_counts[row["declaredNormalizedReading"]] > 1:
            reasons.append("duplicate_in_n2_block")
        if not row["zh"]:
            reasons.append("blank_zh")
        if len(row["zh"]) == 1:
            reasons.append("too_short_zh")
        if not CJK_RE.search(row["zh"]):
            reasons.append("zh_without_cjk")
        if re.search(r"[ぁ-んァ-ヶーA-Za-z]", row["zh"]):
            reasons.append("zh_contains_non_chinese_gloss")
        if row["zh"] == row["writing"] and re.search(r"[ぁ-んァ-ヶー]", row["writing"]):
            reasons.append("zh_matches_japanese_writing")
        if any(BAD_GAME_TEXT_RE.search(value) for value in row.values()):
            reasons.append("bad_game_text")
        if row["script"] not in {"kanji", "hiragana", "katakana"}:
            reasons.append("bad_script")
        if reasons:
            audits.append({
                "line_no": str(index),
                "reading": row["reading"],
                "writing": row["writing"],
                "declaredNormalizedReading": row["declaredNormalizedReading"],
                "zh": row["zh"],
                "script": row["script"],
                "audit_reason": ";".join(reasons),
            })
    return audits


def main() -> None:
    imported, rejected, merged_rows, reject_counts = merge_rows()
    audits = audit_rows(merged_rows)
    write_csv(
        CLEANED_CSV,
        imported,
        ["reading", "writing", "declaredNormalizedReading", "zh", "script", "source_page", "source_column", "source_entry_no", "source_writing"],
    )
    write_csv(
        REJECTED_CSV,
        rejected,
        ["reason", "level", "reading", "writing", "zh", "page", "column", "entry_no", "needs_review", "review_reason"],
    )
    write_csv(
        AUDIT_CSV,
        audits,
        ["line_no", "reading", "writing", "declaredNormalizedReading", "zh", "script", "audit_reason"],
    )

    print(f"imported={len(imported)}")
    print(f"rejected={len(rejected)}")
    print(f"merged_n2_extra_rows={len(merged_rows)}")
    print(f"audit_issues={len(audits)}")
    for reason, count in sorted(reject_counts.items()):
        print(f"{reason}={count}")


if __name__ == "__main__":
    main()
