#!/usr/bin/env python3
"""Merge reviewed N1 OCR rows into the game word data.

The N1 source is OCR-derived, so this script imports conservative rows only,
derives Chinese glosses from OCR context, preserves existing hand-written N1
rows, and writes audit CSVs for post-merge proofreading.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = Path(__file__).resolve().parent
DATA_PATH = PROJECT_ROOT / "web" / "data" / "word_data.js"
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"
SOURCE_CSV = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_corrected.csv"
CANDIDATES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_candidates.csv"
CLEANED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_cleaned_for_game.csv"
REJECTED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_rejected_for_game.csv"
AUDIT_CSV = TOOL_ROOT / "dictionary" / "jlpt_n1_wordlist_import_audit.csv"

CSV_BLOCK_START = "  N1_EXTRA_WORD_ROWS_TEXT: `"
CSV_BLOCK_END = "`,\n  EGGROLLS_N5_WORD_ROWS_TEXT"


JS_ROW_RE = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)
HIRAGANA_RE = re.compile(r"^[ぁ-んー・]+$")
KATAKANA_RE = re.compile(r"^[ァ-ヶー・]+$")
CJK_RE = re.compile(r"[一-龯々〆]")
BAD_READING_RE = re.compile(r"[^ぁ-んァ-ヶー・]")
BAD_GAME_TEXT_RE = re.compile(r"[|`]")
ASCII_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z .+\-]*$")
LATIN_NOISE_RE = re.compile(r"[A-Za-z]{2,}")
ENTRY_MARKER_RE = re.compile(r"^\s*(?:\d{1,3}|[oO]\d?|[iIl]\d?)\s*[|｜]\s*")
EXAMPLE_MARKER_RE = re.compile(r"[図国圏回団較遼串目]|\s[ぁ-ん]{1,4}\s")


READING_CORRECTIONS = {
    "じこくひよう": "じこくひょう",
    "ひようげん": "ひょうげん",
    "びようし": "びようし",
    "ひようし": "ひょうし",
    "ひようばん": "ひょうばん",
    "ひようほん": "ひょうほん",
}

WRITING_CORRECTIONS = {
    ("いっこく", "-刻"): "一刻",
    ("えんがわ", "緑側"): "縁側",
    ("かぶか", "価"): "株価",
    ("ごうい", "合意"): "合意",
    ("こよみ", "大"): "暦",
    ("ざっそう", "雑音"): "雑草",
    ("しょうがい", "障"): "障害",
    ("ぜっぱん", ""): "絶版",
    ("そっけない", "素っ気無い"): "素っ気ない",
    ("べこべぺこ", ""): "ぺこぺこ",
    ("まっき", "未期"): "末期",
    ("ややこしい", ""): "ややこしい",
}

MANUAL_SKIP_READINGS = {
    "素寢約",
    "歷51",
    "LAu3",
    "it-上3",
    "秒3扎tA",
    "上(7了",
    "三3大必",
}

ZH_CORRECTIONS = {
    "あわあ": "尖峰時段、小時",
    "きっかり": "正好、整整",
    "すむうず": "順利、流暢",
    "にゅう": "新的、新式的",
    "すらっくす": "西裝褲、長褲",
    "だるい": "倦怠、發懶",
    "むせる": "嗆到、噎住",
    "おせっかい": "多管閒事",
    "ぴんぴん": "硬朗、健壯",
    "どぶ": "水溝、陰溝",
    "こんてすと": "比賽、競賽",
    "ろおぷ": "繩索",
    "ぼると": "螺栓、伏特",
    "おおけえ": "可以、沒問題",
    "いっこく": "一刻、片刻",
    "おくらす": "延遲、拖延",
    "ごおるでんたいむ": "黃金時段",
    "こうりつ": "效率",
    "さっきゅう・そうきゅう": "火速、盡快",
    "じこくひょう": "時刻表",
    "じさ": "時差",
    "すみやか": "迅速",
    "ひょうじゅんか": "標準化",
    "べすとせらあ": "暢銷書",
    "ついやす": "花費、耗費",
    "ひどり": "日期、日程",
    "ひやけ": "曬黑、日曬",
    "ねぐるしい": "睡不安穩、難以入睡",
    "みのうえ": "身世、境遇",
    "おおらか": "豁達、寬宏",
    "したしまれる": "受人親近、受喜愛",
    "しずめる": "使沉下、鎮定",
    "さらなる": "更加、進一步",
    "みたす": "滿足、填滿",
    "とぐ": "磨利、研磨",
    "したてる": "縫製、培養成",
    "じゅんじる・じゅんずる": "依照、按照",
    "きがむく": "有興致、想做",
    "とうとい": "尊貴、珍貴",
    "つらぬく": "貫穿、貫徹",
    "でなおし": "重新開始、重來",
    "けがれる": "弄髒、玷汙",
    "しぶい": "澀、素雅",
    "おどす": "威脅、恐嚇",
    "けがれ": "汙穢、汙點",
    "おろそか": "草率、疏忽",
    "うちけし": "否定、取消",
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
    blocks: list[str] = [
        slice_between(word_data, "  RAW_WORDS:", "  N4_BASE_WORD_ROWS:"),
        slice_between(word_data, "  N4_BASE_WORD_ROWS:", "  N4_EXTRA_WORD_ROWS_TEXT:"),
        slice_between(word_data, "  N3_BASE_WORD_ROWS:", "  N3_RESERVED_UPPER_LEVEL_READING_VALUES:"),
        slice_between(word_data, "  N1_BASE_WORD_ROWS:", "  N1_EXTRA_WORD_ROWS_TEXT:"),
        slice_between(index_html, "      const N2_BASE_WORD_ROWS = [", "      ];\n\n      const N2_LOWER_LEVEL_READINGS"),
    ]
    readings: set[str] = set()
    for block in blocks:
        for row in parse_js_rows(block):
            readings.add(normalize_kana_reading(row[1] or row[3]))

    for name, end_marker in [
        ("N4_EXTRA_WORD_ROWS_TEXT", "`,\n  N4_CSV_WORD_ROWS_TEXT"),
        ("N4_CSV_WORD_ROWS_TEXT", "`,\n  N3_BASE_WORD_ROWS"),
        ("N3_EXTRA_WORD_ROWS_TEXT", "`,\n  N2_EXTRA_WORD_ROWS_TEXT"),
        ("N2_EXTRA_WORD_ROWS_TEXT", "`,\n  N1_BASE_WORD_ROWS"),
    ]:
        for row in parse_pipe_rows(extract_word_text_property(word_data, name, end_marker)):
            if "invalid" not in row:
                readings.add(normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"]))

    n1_existing = [
        row for row in parse_pipe_rows(extract_word_text_property(word_data, "N1_EXTRA_WORD_ROWS_TEXT", CSV_BLOCK_END))
        if "invalid" not in row
    ]
    return readings, n1_existing


def normalize_entry_no(value: str | None) -> str:
    value = nfkc(value).lower().replace("o", "0").replace("i", "1").replace("l", "1")
    return value.zfill(2) if value.isdigit() else value


def load_candidate_contexts() -> tuple[
    dict[tuple[str, str, str, str, str], str],
    dict[tuple[str, str, str, str], str],
    dict[tuple[str, str, str], str],
]:
    exact: dict[tuple[str, str, str, str, str], str] = {}
    by_reading: dict[tuple[str, str, str, str], str] = {}
    by_location: dict[tuple[str, str, str], str] = {}
    if not CANDIDATES_CSV.exists():
        return exact, by_reading, by_location

    with CANDIDATES_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            reading = normalize_kana_reading(row.get("headword", ""))
            writing = nfkc(row.get("bracket"))
            page = nfkc(row.get("page"))
            column = nfkc(row.get("column"))
            entry_no = normalize_entry_no(row.get("entry_no"))
            context = nfkc(row.get("ocr_context"))
            if not context:
                continue
            exact.setdefault((reading, writing, page, column, entry_no), context)
            by_reading.setdefault((reading, page, column, entry_no), context)
            by_location.setdefault((page, column, entry_no), context)
    return exact, by_reading, by_location


def cleanup_gloss(value: str) -> str:
    value = nfkc(value).replace("・", "、")
    value = ENTRY_MARKER_RE.sub("", value)
    value = re.split(r"[。.!?！？]", value, maxsplit=1)[0]
    value = EXAMPLE_MARKER_RE.split(value, maxsplit=1)[0]
    value = re.sub(r"N[12345]", "", value)
    value = re.sub(r"^[^一-龯々〆]+", "", value)
    value = re.sub(r"^(名|副|形動|感|接|代|連体|漢造|自|他|五|上一|下一|サ|俗|敬|謙|文|全|便|客|所|電|避|寝|祀|嘱|再|件|和)[)）・、:;\s]+", "", value)
    value = re.sub(r"[ぁ-んァ-ヶー]+", "", value)
    value = re.sub(r"[()\[\]{}<>「」『』【】|/@①-⑳0-9A-Za-z~^_+=#$%&*]+", " ", value)
    value = re.sub(r"[、,，;；:：\s]+", "、", value)
    value = value.strip("、-—'\"“”")
    parts = [part for part in value.split("、") if part and len(part) <= 12]
    while len(parts) > 1 and len(parts[0]) == 1:
        parts.pop(0)
    gloss = "、".join(parts)
    return gloss[:48].rstrip("、")


def extract_zh(context: str, writing: str) -> str:
    segments = [segment.strip() for segment in nfkc(context).split(" / ") if segment.strip()]
    pieces: list[str] = []
    for segment in segments[1:4]:
        gloss = cleanup_gloss(segment)
        if CJK_RE.search(gloss) and len(gloss) >= 2 and not LATIN_NOISE_RE.search(gloss):
            pieces.append(gloss)
        if len("、".join(pieces)) >= 24:
            break
    if pieces:
        return "、".join(pieces)[:48].rstrip("、")
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


def replace_n1_block(word_data: str, rows: list[dict[str, str]]) -> str:
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


def source_word_keys_for_cleanup() -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            if row.get("needs_review", "").strip():
                continue
            reading = READING_CORRECTIONS.get(nfkc(row.get("reading")), nfkc(row.get("reading")))
            writing = WRITING_CORRECTIONS.get((reading, nfkc(row.get("writing"))), nfkc(row.get("writing")))
            if not reading or BAD_READING_RE.search(reading):
                continue
            if not writing:
                writing = reading
            script = infer_script(reading, writing)
            display_writing = reading if script == "katakana" else writing
            keys.add((normalize_kana_reading(reading), display_writing))
    return keys


def merge_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], Counter[str]]:
    word_data = DATA_PATH.read_text(encoding="utf-8")
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    lower_and_base_readings, existing_n1_rows = existing_readings(word_data, index_html)
    source_cleanup_keys = source_word_keys_for_cleanup()
    existing_n1_rows = [
        row for row in existing_n1_rows
        if (normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"]), row["writing"]) not in source_cleanup_keys
    ]
    existing_n1_readings = {
        normalize_kana_reading(row["reading"] or row["declaredNormalizedReading"])
        for row in existing_n1_rows
    }
    appended_readings: set[str] = set()
    exact_contexts, reading_contexts, location_contexts = load_candidate_contexts()
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
        })

    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            original_reading = nfkc(row.get("reading"))
            original_writing = nfkc(row.get("writing"))
            reading = READING_CORRECTIONS.get(original_reading, original_reading)
            writing = WRITING_CORRECTIONS.get((reading, original_writing), original_writing)
            normalized = normalize_kana_reading(reading)
            page = nfkc(row.get("page"))
            column = nfkc(row.get("column"))
            entry_no = normalize_entry_no(row.get("entry_no"))

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
                reject(row, "duplicate_lower_or_base_reading", reading, writing)
                continue
            if not writing:
                writing = reading
            if BAD_GAME_TEXT_RE.search(reading) or BAD_GAME_TEXT_RE.search(writing):
                reject(row, "bad_game_text", reading, writing)
                continue

            context = exact_contexts.get((normalized, writing, page, column, entry_no), "")
            if not context:
                context = reading_contexts.get((normalized, page, column, entry_no), "")
            if not context:
                context = location_contexts.get((page, column, entry_no), "")
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
            if normalized in existing_n1_readings:
                reject(row, "duplicate_existing_n1_reading", reading, writing, zh)
                continue
            if normalized in appended_readings:
                reject(row, "duplicate_source_reading", reading, writing, zh)
                continue
            appended_readings.add(normalized)
            import_row = {
                "reading": reading,
                "writing": display_writing,
                "declaredNormalizedReading": normalized,
                "zh": zh,
                "script": script,
                "source_page": page,
                "source_column": column,
                "source_entry_no": entry_no,
                "source_writing": writing,
            }
            imported.append(import_row)

    merged_rows = existing_n1_rows + [
        {field: row[field] for field in ["reading", "writing", "declaredNormalizedReading", "zh", "script"]}
        for row in imported
        if row["declaredNormalizedReading"] in appended_readings
    ]
    DATA_PATH.write_text(replace_n1_block(word_data, merged_rows), encoding="utf-8")
    return imported, rejected, merged_rows, reject_counts


def audit_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    audits: list[dict[str, str]] = []
    word_key_counts = Counter((row["declaredNormalizedReading"], row["writing"]) for row in rows)
    for index, row in enumerate(rows, start=1):
        reasons: list[str] = []
        if word_key_counts[(row["declaredNormalizedReading"], row["writing"])] > 1:
            reasons.append("duplicate_in_n1_block")
        if not row["zh"]:
            reasons.append("blank_zh")
        if len(row["zh"]) == 1:
            reasons.append("too_short_zh")
        if not CJK_RE.search(row["zh"]):
            reasons.append("zh_without_cjk")
        if re.search(r"[ぁ-んァ-ヶーA-Za-z]", row["zh"]):
            reasons.append("zh_contains_non_chinese_gloss")
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
        ["reason", "level", "reading", "writing", "zh", "page", "column", "entry_no", "needs_review"],
    )
    write_csv(
        AUDIT_CSV,
        audits,
        ["line_no", "reading", "writing", "declaredNormalizedReading", "zh", "script", "audit_reason"],
    )

    print(f"imported={len(imported)}")
    print(f"rejected={len(rejected)}")
    print(f"merged_n1_extra_rows={len(merged_rows)}")
    print(f"audit_issues={len(audits)}")
    for reason, count in sorted(reject_counts.items()):
        print(f"{reason}={count}")


if __name__ == "__main__":
    main()
