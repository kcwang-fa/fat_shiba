#!/usr/bin/env python3
"""Build browser-ready learning metadata for Fat Shiba words."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CSV = PROJECT_ROOT / "tools" / "dictionary" / "word_meta.csv"
N5_EXAMPLES_CSV = PROJECT_ROOT / "tools" / "dictionary" / "n5_examples.csv"
N4_EXAMPLES_CSV = PROJECT_ROOT / "tools" / "dictionary" / "n4_examples.csv"
N1_EXAMPLES_CSV = PROJECT_ROOT / "tools" / "dictionary" / "n1_examples.csv"
WORD_DATA_JS = PROJECT_ROOT / "web" / "data" / "word_data.js"
WORD_LEVEL_BUILDER_JS = PROJECT_ROOT / "tools" / "dictionary" / "build_word_level_data.js"
INDEX_HTML = PROJECT_ROOT / "web" / "index.html"
OUTPUT_JS = PROJECT_ROOT / "web" / "data" / "word_meta.js"
EGGROLLS_IMPORTED_CSV = PROJECT_ROOT / "outputs" / "eggrolls_JLPT10k_v3_5_word_import" / "eggrolls_imported_words.csv"
EGGROLLS_NOTES_TSV = PROJECT_ROOT / "outputs" / "eggrolls_JLPT10k_v3_5_apkg_parse" / "notes.tsv"

LEVEL_EXAMPLE_CSVS = {
    "n5": N5_EXAMPLES_CSV,
    "n4": N4_EXAMPLES_CSV,
    "n1": N1_EXAMPLES_CSV,
}

POS_LABELS = {
    "noun": "名詞",
    "pronoun": "代名詞",
    "determiner": "連體詞",
    "numeric": "數詞",
    "verb": "動詞",
    "i_adjective": "い形容詞",
    "na_adjective": "な形容詞",
    "adverb": "副詞",
    "particle": "助詞",
    "conjunction": "接續詞",
    "interjection": "感動詞",
    "expression": "慣用表現",
    "katakana": "外來語",
    "suru_noun": "する名詞",
    "counter": "助數詞",
    "prefix": "接頭語",
    "suffix": "接尾語",
    "bound_morpheme": "造語成分",
    "auxiliary_verb": "補助動詞",
    "final_particle": "終助詞",
}

VERB_CLASS_LABELS = {
    "ichidan": "一段動詞",
    "godan": "五段動詞",
    "godan_iku_exception": "五段動詞（行く例外）",
    "honorific_ru": "尊敬語る動詞",
    "suru": "する動詞",
    "kuru": "来る",
    "aru": "ある",
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

EXPECTED_EXAMPLE_FIELDS = [
    "id",
    "example_ja",
    "example_zh",
]

JS_ROW_RE = re.compile(
    r'\["([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\]'
)
CORE_LEVEL_ID_RE = re.compile(r"^(n[1-5])_\d{4}$")
HTML_TAG_RE = re.compile(r"<[^>]+>")

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


def n5_ids(start: int, end: int) -> set[str]:
    return {f"n5_{number:04d}" for number in range(start, end + 1)}


N5_VERB_IDS = (
    n5_ids(81, 98)
    | n5_ids(315, 400)
    | n5_ids(623, 652)
)

N5_ICHIDAN_VERB_IDS = {
    "n5_0084", "n5_0086", "n5_0095", "n5_0096",
    "n5_0316", "n5_0323", "n5_0324", "n5_0328", "n5_0329",
    "n5_0336", "n5_0337", "n5_0338", "n5_0339", "n5_0340",
    "n5_0351", "n5_0357", "n5_0360", "n5_0361", "n5_0363",
    "n5_0367", "n5_0373", "n5_0383", "n5_0386", "n5_0393",
    "n5_0394", "n5_0397", "n5_0398", "n5_0399", "n5_0400",
    "n5_0626", "n5_0628", "n5_0629", "n5_0631", "n5_0632",
    "n5_0635", "n5_0636", "n5_0637", "n5_0638", "n5_0647",
    "n5_0651", "n5_0652",
}

N5_KURU_VERB_IDS = {"n5_0082"}
N5_ARU_VERB_IDS = {"n5_0354"}
N5_IKU_EXCEPTION_VERB_IDS = {"n5_0081", "n5_0639"}

N5_I_ADJECTIVE_IDS = (
    n5_ids(68, 80)
    | n5_ids(277, 280)
    | n5_ids(292, 314)
    | n5_ids(599, 610)
)

N5_NA_ADJECTIVE_IDS = (
    n5_ids(281, 291)
    | n5_ids(611, 616)
)

N5_SURU_NOUN_IDS = {
    "n5_0099", "n5_0101", "n5_0187", "n5_0203", "n5_0455",
    "n5_0478", "n5_0570", "n5_0617", "n5_0618", "n5_0619",
    "n5_0620", "n5_0621", "n5_0622", "n5_0653", "n5_0654",
}

N5_PRONOUN_IDS = (
    n5_ids(109, 111)
    | n5_ids(116, 134)
)

N5_DETERMINER_IDS = n5_ids(112, 115)

N5_NUMERIC_IDS = (
    n5_ids(405, 425)
    | n5_ids(659, 683)
)

N5_ADVERB_IDS = {
    "n5_0012", "n5_0148",
    *n5_ids(431, 446),
    *n5_ids(449, 454),
}

N5_INTERJECTION_IDS = (
    n5_ids(684, 699)
    | {"n5_0447", "n5_0448"}
)

N5_PARTICLE_IDS = n5_ids(704, 709)
N5_CONJUNCTION_IDS = n5_ids(710, 712)

U_ROW_ENDINGS = set("うくぐすつぬぶむる")
N4_HIRAGANA_VERB_READINGS = {
    "いらっしゃる",
    "おいでになる",
    "おっしゃる",
    "しまう",
    "なさる",
    "てしまう",
}
N4_EXPRESSION_IDS = {
    "n4_0347", "n4_0618", "n4_0619", "n4_0620", "n4_0621", "n4_0622",
    "n4_0833", "n4_0834",
}
N4_HONORIFIC_RU_READINGS = {
    "いらっしゃる",
    "おっしゃる",
    "なさる",
    "くださる",
}
N4_GODAN_RU_READINGS = {
    "まいる",
    "かぎる",
}
N4_I_ADJECTIVE_NOUN_READINGS = {
    "おいわい",
    "ちがい",
    "てつだい",
}
N4_I_ADJECTIVE_READINGS = {
    "はずかしい", "あさい", "うつくしい", "きびしい", "さびしい",
    "すごい", "すばらしい", "ただしい", "にがい", "ひどい",
    "ふかい", "めずらしい", "やわらかい", "うまい", "おしい",
    "おそろしい", "かたい", "かなしい", "かまわない", "こい",
    "すくない", "つごうがいい", "なつかしい", "わかりやすい",
    "わすれっぽい", "おかしい", "こまかい", "ねむたい", "おおい",
    "こわい", "うれしい", "よろしい",
}
N4_NA_ADJECTIVE_WRITINGS = {
    "危険", "親切", "大切", "確か", "特別", "必要", "複雑", "普通",
    "残念", "簡単", "丁寧", "適当", "熱心", "楽", "安定", "嫌",
    "当たり前", "可哀想", "十分", "丈夫", "盛ん", "失礼", "心配",
    "得意", "大嫌い", "積極的",
}
N4_ADVERB_READINGS = {
    "かならず", "しばらく", "すっかり", "ずいぶん", "ぜひ", "だいぶ",
    "なるべく", "なるほど", "はっきり", "いちおう", "いっしょうけんめい",
    "いまにも", "いきなり", "いくらでも", "めったに", "あいかわらず",
    "このごろ", "とうとう", "もうすぐ", "たしか", "とくに", "べつに",
    "ほとんど", "わりあいに", "こう", "もし", "いっぱい", "だいたい",
    "わりあい",
}
N4_CONJUNCTION_READINGS = {
    "すると", "それで", "それに", "だから",
}
N4_DETERMINER_READINGS = {
    "あんな",
    "おおきな",
    "ちいさな",
    "ひつような",
}
N4_KATAKANA_SURU_READINGS = {
    "インストール",
    "キャンセル",
    "クリック",
    "チェック",
}
N4_SUFFIX_OR_AFFIX_READINGS = {
    "おき", "ばい", "さま", "せい", "にくい", "ながら",
}

N1_I_ADJECTIVE_READINGS = {
    "あくどい", "いちじるしい", "おびただしい", "わずらわしい",
    "あっけない", "こいしい", "こころよい", "しぶとい",
    "すがすがしい", "すばしっこい", "せつない", "そっけない",
    "たくましい", "だるい", "とぼしい", "なだかい",
    "なにげない", "なまぐさい", "なまぬるい", "なやましい",
    "のぞましい", "はかない", "ばかばかしい", "まぎらわしい",
    "まちどおしい", "みぐるしい", "みすぼらしい", "むなしい",
    "めざましい", "めまぐるしい", "もろい", "ややこしい",
}

N1_NA_ADJECTIVE_WRITINGS = {
    "厳か", "速やか", "切実", "端的", "頻繁", "鮮やか",
    "あべこべ", "あやふや", "円満", "大袈裟", "疎か",
    "微か", "気障", "気まぐれ", "生真面目", "煌びやか",
    "健全", "巧妙", "滑稽", "柔軟", "健やか", "巧み",
    "和やか", "遥か", "控えめ", "密か", "不意", "ふんだん",
    "全う", "無限", "明瞭", "憂鬱", "有望", "良好",
}

N1_ADVERB_READINGS = {
    "あくせく", "いたって", "いささか", "いちがいに", "いっさい",
    "いやいや", "おおむね", "おどおど", "かねて", "きゅうきょ",
    "くっきり", "さぞ", "さも", "しいて", "じゃっかん",
    "しゅうし", "すこぶる", "ずばり", "だんぜん", "ちやほや",
    "つくづく", "なにとぞ", "はなはだ", "ひいては", "ひたすら",
    "むろん", "もっぱら", "よほど", "ろくに",
}

N1_CONJUNCTION_READINGS = {
    "ならびに",
}

N1_SURU_NOUN_READINGS = {
    "かいしゅう", "かんげん", "きゅうさい", "けんしょう",
    "こうそく", "さいけん", "しさ", "じゅんかん", "しょち",
    "せいさい", "そうさい", "そくしん", "たいしょ", "ちくせき",
    "ていけい", "はいりょ", "はあく", "ほうかつ", "ゆうずう",
    "ようにん", "ろうきゅうか", "ひょうじゅんか", "いっかつ",
    "いっぺん", "かいにゅう", "かさん", "きょうかん",
    "けいべつ", "こくはく", "ざつだん", "ちょうはつ", "てはい",
    "どうかん", "どうじょう", "はいし",
}

N1_NOUN_READINGS = {
    "うちけし", "とりしまり", "ひめい", "ほっさ",
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


def clean_anki_text(value: str | None) -> str:
    text = HTML_TAG_RE.sub("", value or "")
    return text.replace("&nbsp;", " ").strip()


def row_dict(word_id: str, reading: str, writing: str, normalized: str, zh: str, script: str) -> dict[str, str]:
    return {
        "id": word_id,
        "reading": reading,
        "writing": writing,
        "normalizedReading": normalized,
        "zh": zh,
        "script": script,
    }


def word_key(reading: str, writing: str, normalized: str) -> tuple[str, str]:
    return normalize_kana_reading(reading or normalized), writing.strip()


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


def build_imported_word_rows(prefix: str, rows_text: str, excluded_keys: set[tuple[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen_keys = set(excluded_keys)

    for raw_row in rows_text.strip().splitlines():
        row = raw_row.strip()
        if not row:
            continue
        parts = [part.strip() for part in row.split("|")]
        if len(parts) != 5:
            raise ValueError(f"Invalid {prefix} imported word row: {row}")
        reading, writing, declared_normalized_reading, zh, script = parts
        normalized = normalize_kana_reading(reading or declared_normalized_reading)
        key = word_key(reading, writing, declared_normalized_reading)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append(row_dict(
            f"{prefix}_{len(rows) + 1:04d}",
            reading,
            writing,
            normalized,
            zh,
            script,
        ))
    return rows


def reading_set(rows: list[dict[str, str]]) -> set[str]:
    return {normalize_kana_reading(row["reading"] or row["normalizedReading"]) for row in rows}


def key_set(rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    return {word_key(row["reading"], row["writing"], row["normalizedReading"]) for row in rows}


def load_word_index() -> dict[str, dict[str, str]]:
    word_data = WORD_DATA_JS.read_text(encoding="utf-8")
    word_level_builder = WORD_LEVEL_BUILDER_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")
    explicit_rows = (
        explicit_word_rows(word_data)
        + explicit_word_rows(word_level_builder)
        + explicit_word_rows(index_html)
    )
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

    n5_eggrolls_rows = build_imported_word_rows(
        "n5_egg",
        extract_pipe_text(word_data, "EGGROLLS_N5_WORD_ROWS_TEXT"),
        key_set(n5_rows),
    )
    n4_eggrolls_rows = build_imported_word_rows(
        "n4_egg",
        extract_pipe_text(word_data, "EGGROLLS_N4_WORD_ROWS_TEXT"),
        key_set([*n5_rows, *n5_eggrolls_rows, *n4_word_rows]),
    )
    n3_eggrolls_rows = build_imported_word_rows(
        "n3_egg",
        extract_pipe_text(word_data, "EGGROLLS_N3_WORD_ROWS_TEXT"),
        key_set([*n5_rows, *n5_eggrolls_rows, *n4_word_rows, *n4_eggrolls_rows, *n3_word_rows]),
    )
    n2_eggrolls_rows = build_imported_word_rows(
        "n2_egg",
        extract_pipe_text(word_data, "EGGROLLS_N2_WORD_ROWS_TEXT"),
        key_set([
            *n5_rows,
            *n5_eggrolls_rows,
            *n4_word_rows,
            *n4_eggrolls_rows,
            *n3_word_rows,
            *n3_eggrolls_rows,
            *n2_base_rows,
            *n2_extra_rows,
        ]),
    )
    n1_eggrolls_rows = build_imported_word_rows(
        "n1_egg",
        extract_pipe_text(word_data, "EGGROLLS_N1_WORD_ROWS_TEXT"),
        key_set([
            *n5_rows,
            *n5_eggrolls_rows,
            *n4_word_rows,
            *n4_eggrolls_rows,
            *n3_word_rows,
            *n3_eggrolls_rows,
            *n2_base_rows,
            *n2_extra_rows,
            *n2_eggrolls_rows,
            *n1_base_rows,
            *n1_extra_rows,
        ]),
    )

    words: dict[str, dict[str, str]] = {}
    for row in [
        *n5_rows,
        *n5_eggrolls_rows,
        *n4_word_rows,
        *n4_eggrolls_rows,
        *n3_word_rows,
        *n3_eggrolls_rows,
        *n2_base_rows,
        *n2_extra_rows,
        *n2_eggrolls_rows,
        *n1_base_rows,
        *n1_extra_rows,
        *n1_eggrolls_rows,
    ]:
        words[row["id"]] = row
    return words


def without_last_kana(value: str) -> str:
    chars = list(value)
    if not chars:
        raise ValueError("Cannot conjugate a blank verb")
    return "".join(chars[:-1])


def verb_forms(dictionary_form: str, verb_class: str) -> dict[str, str]:
    dictionary_form = dictionary_form.split("・", 1)[0].strip()

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

    if verb_class == "honorific_ru":
        if not dictionary_form.endswith("る"):
            raise ValueError(f"Honorific ru verb must end with る: {dictionary_form}")
        stem = dictionary_form[:-1]
        return {
            "dictionary": dictionary_form,
            "masu": f"{stem}います",
            "te": f"{stem}って",
            "ta": f"{stem}った",
            "nai": f"{stem}らない",
        }

    if verb_class == "aru":
        return {
            "dictionary": dictionary_form,
            "masu": "あります",
            "te": "あって",
            "ta": "あった",
            "nai": "ない",
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


def infer_pos(row: dict[str, str]) -> str:
    word_id = row["id"]
    if "_egg_" in word_id:
        return "noun"
    if word_id.startswith("n1_"):
        return infer_n1_pos(row)
    if word_id.startswith("n4_"):
        return infer_n4_pos(row)
    if word_id in N5_VERB_IDS:
        return "verb"
    if word_id in N5_I_ADJECTIVE_IDS:
        return "i_adjective"
    if word_id in N5_NA_ADJECTIVE_IDS:
        return "na_adjective"
    if word_id in N5_SURU_NOUN_IDS:
        return "suru_noun"
    if word_id in N5_PRONOUN_IDS:
        return "pronoun"
    if word_id in N5_DETERMINER_IDS:
        return "determiner"
    if word_id in N5_NUMERIC_IDS:
        return "numeric"
    if word_id in N5_ADVERB_IDS:
        return "adverb"
    if word_id in N5_INTERJECTION_IDS:
        return "interjection"
    if word_id in N5_PARTICLE_IDS:
        return "particle"
    if word_id in N5_CONJUNCTION_IDS:
        return "conjunction"
    if row["script"] == "katakana":
        return "katakana"
    return "noun"


def is_n4_verb(row: dict[str, str]) -> bool:
    reading = row["reading"]
    writing = row["writing"]
    if row["id"] in N4_EXPRESSION_IDS:
        return False
    if reading in N4_HIRAGANA_VERB_READINGS:
        return True
    if reading.endswith("する"):
        return True
    if writing.endswith("する"):
        return True
    if writing.split("・", 1)[0].endswith(tuple(U_ROW_ENDINGS)):
        return True
    return False


def infer_n4_pos(row: dict[str, str]) -> str:
    reading = row["reading"]
    writing = row["writing"]
    if row["id"] in N4_EXPRESSION_IDS:
        return "expression"
    if reading in N4_CONJUNCTION_READINGS:
        return "conjunction"
    if reading in N4_DETERMINER_READINGS:
        return "determiner"
    if reading in N4_ADVERB_READINGS:
        return "adverb"
    if reading in N4_SUFFIX_OR_AFFIX_READINGS:
        return "suffix"
    if is_n4_verb(row):
        return "verb"
    if writing in N4_NA_ADJECTIVE_WRITINGS:
        return "na_adjective"
    if reading in N4_KATAKANA_SURU_READINGS:
        return "suru_noun"
    if looks_like_suru_noun(row):
        return "suru_noun"
    if row["script"] == "katakana":
        return "katakana"
    if reading in N4_I_ADJECTIVE_READINGS:
        return "i_adjective"
    return "noun"


def infer_n1_pos(row: dict[str, str]) -> str:
    reading = row["reading"]
    writing = row["writing"]
    if reading in N1_CONJUNCTION_READINGS:
        return "conjunction"
    if reading in N1_NOUN_READINGS:
        return "noun"
    if reading in N1_ADVERB_READINGS:
        return "adverb"
    if reading in N1_SURU_NOUN_READINGS:
        return "suru_noun"
    if reading in N1_I_ADJECTIVE_READINGS:
        return "i_adjective"
    if writing in N1_NA_ADJECTIVE_WRITINGS:
        return "na_adjective"
    if is_n1_verb(row):
        return "verb"
    if looks_like_suru_noun(row):
        return "suru_noun"
    if row["script"] == "katakana":
        return "katakana"
    return "noun"


def is_n1_verb(row: dict[str, str]) -> bool:
    reading = row["reading"]
    writing = row["writing"]
    if reading.endswith("する") or writing.endswith("する"):
        return True
    if reading in N1_I_ADJECTIVE_READINGS or writing in N1_NA_ADJECTIVE_WRITINGS:
        return False
    return writing.split("・", 1)[0].endswith(tuple(U_ROW_ENDINGS))


def looks_like_suru_noun(row: dict[str, str]) -> bool:
    reading = row["reading"]
    writing = row["writing"]
    zh = row["zh"]
    if not writing:
        return False
    if writing.endswith("式"):
        return False
    if row["script"] == "katakana":
        return False
    action_keywords = (
        "打招呼", "介紹", "經驗", "故障", "準備", "失敗", "出發", "招待",
        "說明", "商量", "入學", "約定", "聯絡", "教育", "競爭", "研究",
        "參觀", "合格", "畢業", "複習", "翻譯", "輸出", "進口", "預習",
        "利用", "營業", "活動", "觀光", "學習", "回國", "寄宿", "就職",
        "介紹", "用餐", "擔心", "發表", "出差", "交流", "感動", "入力",
        "插入", "轉寄", "檢查", "計畫", "帶路", "預定", "探病", "慰問",
        "游泳", "注意", "準備", "休息", "會計", "結帳", "新增", "建立新檔",
        "反對", "計算", "送信", "傳送", "收信", "接收", "保存", "取消",
        "輸入", "轉送", "回信", "確認", "安裝",
    )
    return any(keyword in zh for keyword in action_keywords)


def infer_verb_class(word_id: str) -> str:
    if word_id in N5_KURU_VERB_IDS:
        return "kuru"
    if word_id in N5_ARU_VERB_IDS:
        return "aru"
    if word_id in N5_IKU_EXCEPTION_VERB_IDS:
        return "godan_iku_exception"
    if word_id in N5_ICHIDAN_VERB_IDS:
        return "ichidan"
    return "godan"


def infer_verb_class_for_word(row: dict[str, str]) -> str:
    if row["id"].startswith("n5_"):
        return infer_verb_class(row["id"])
    reading = row["reading"]
    dictionary_form = row["writing"] or reading
    dictionary_form = dictionary_form.split("・", 1)[0].strip()
    if reading in N4_HONORIFIC_RU_READINGS:
        return "honorific_ru"
    if reading.endswith("する") or dictionary_form.endswith("する"):
        return "suru"
    if reading.endswith("くる") or dictionary_form.endswith("来る"):
        return "kuru"
    if reading in N4_GODAN_RU_READINGS:
        return "godan"
    if reading.endswith("る"):
        chars = list(reading)
        previous = chars[-2] if len(chars) >= 2 else ""
        return "ichidan" if kana_vowel(previous) in {"i", "e"} else "godan"
    return "godan"


def auto_example(row: dict[str, str], pos: str, forms: dict[str, str] | None = None) -> dict[str, str]:
    display = row["writing"] or row["reading"]
    zh = row["zh"]
    if pos == "verb" and forms:
        return {
            "ja": f"「{forms['dictionary']}」は動詞です。",
            "zh": f"「{display}」是動詞，意思是「{zh}」。",
        }
    if pos == "suru_noun" and forms:
        return {
            "ja": f"{forms['masu']}。",
            "zh": f"進行「{zh}」。",
        }
    if pos in {"i_adjective", "na_adjective"}:
        return {
            "ja": f"これは{display}です。",
            "zh": f"這個是「{zh}」。",
        }
    if pos in {"particle", "conjunction", "interjection", "expression", "adverb", "determiner"}:
        return {
            "ja": f"「{display}」を使います。",
            "zh": f"使用「{display}」這個詞。",
        }
    return {
        "ja": f"これは{display}です。",
        "zh": f"這是「{zh}」。",
    }


def is_core_level_id(word_id: str, level: str) -> bool:
    match = CORE_LEVEL_ID_RE.fullmatch(word_id)
    return bool(match and match.group(1) == level)


def load_level_examples(level: str, words: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    examples_path = LEVEL_EXAMPLE_CSVS[level]
    examples: dict[str, dict[str, str]] = {}
    if not examples_path.exists():
        return examples

    with examples_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != EXPECTED_EXAMPLE_FIELDS:
            raise ValueError(f"Expected example CSV fields {EXPECTED_EXAMPLE_FIELDS}, got {reader.fieldnames}")

        for line_no, row in enumerate(reader, start=2):
            word_id = (row.get("id") or "").strip()
            example_ja = (row.get("example_ja") or "").strip()
            example_zh = (row.get("example_zh") or "").strip()
            if not word_id:
                raise ValueError(f"Line {line_no}: id is required")
            if word_id in examples:
                raise ValueError(f"Line {line_no}: duplicate example id {word_id}")
            if word_id not in words:
                raise ValueError(f"Line {line_no}: unknown example id {word_id}")
            if not is_core_level_id(word_id, level):
                raise ValueError(f"Line {line_no}: example CSV only accepts core {level.upper()} ids")
            if not example_ja or not example_zh:
                raise ValueError(f"Line {line_no}: example_ja and example_zh are required")
            examples[word_id] = {"ja": example_ja, "zh": example_zh}

    missing = sorted(
        word_id for word_id in words
        if is_core_level_id(word_id, level) and word_id not in examples
    )
    if missing:
        sample = ", ".join(missing[:8])
        raise ValueError(f"{level.upper()} examples missing {len(missing)} ids: {sample}")

    return examples


def load_examples(words: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    examples: dict[str, dict[str, str]] = {}
    for level in LEVEL_EXAMPLE_CSVS:
        examples.update(load_level_examples(level, words))
    return examples


def first_eggrolls_example(note: dict[str, str]) -> dict[str, str] | None:
    for index in range(1, 5):
        ja = clean_anki_text(note.get(f"SentKanji{index}"))
        zh = clean_anki_text(note.get(f"SentDefTC{index}"))
        if ja and zh:
            return {"ja": ja, "zh": zh}
    return None


def japanese_sentence(text: str) -> str:
    text = text.strip()
    if not text or text.endswith(("。", "！", "？", "」", ".", "!", "?")):
        return text
    return f"{text}。"


def best_eggrolls_example(note: dict[str, str]) -> dict[str, str] | None:
    candidates: list[tuple[int, str, str]] = []
    for index in range(1, 5):
        ja = clean_anki_text(note.get(f"SentKanji{index}"))
        zh = clean_anki_text(note.get(f"SentDefTC{index}"))
        if not ja or not zh:
            continue
        score = len(ja)
        if "。" in ja or "、" in ja:
            score += 20
        if len(ja) >= 14:
            score += 10
        candidates.append((score, ja, zh))
    if not candidates:
        return None

    _, ja, zh = max(candidates, key=lambda candidate: candidate[0])
    return {"ja": japanese_sentence(ja), "zh": zh}


def deepen_short_n1_example(example: dict[str, str]) -> dict[str, str]:
    ja = example["ja"].strip()
    zh = example["zh"].strip()
    return {"ja": japanese_sentence(ja), "zh": zh}


def eggrolls_pos_config(source_pos: str) -> tuple[str, str, str]:
    parts = {part.strip() for part in source_pos.split("・") if part.strip()}

    transitivity = ""
    if any(part.startswith("自他動") for part in parts):
        transitivity = "both"
    elif any(part.startswith("自動") for part in parts):
        transitivity = "intransitive"
    elif any(part.startswith("他動") for part in parts):
        transitivity = "transitive"

    verb_class = ""
    if any(part.endswith("1") for part in parts if "動" in part):
        verb_class = "godan"
    elif any(part.endswith("2") for part in parts if "動" in part):
        verb_class = "ichidan"
    elif any(part.endswith("3") for part in parts if "動" in part):
        verb_class = "suru"

    if "名" in parts and verb_class == "suru":
        return "suru_noun", "suru", transitivity
    if any("補動" == part for part in parts) and not transitivity:
        return "auxiliary_verb", "", ""
    if verb_class:
        return "verb", verb_class, transitivity
    if "イ形" in parts or "補形" in parts:
        return "i_adjective", "", ""
    if "ナ形" in parts:
        return "na_adjective", "", ""
    if "副助" in parts:
        return "particle", "", ""
    if "終助" in parts:
        return "final_particle", "", ""
    if "接頭" in parts:
        return "prefix", "", ""
    if "接尾" in parts:
        return "suffix", "", ""
    if "造" in parts:
        return "bound_morpheme", "", ""
    if "代" in parts:
        return "pronoun", "", ""
    if "連体" in parts:
        return "determiner", "", ""
    if "接" in parts:
        return "conjunction", "", ""
    if "感" in parts:
        return "interjection", "", ""
    if "連語" in parts or "成句" in parts:
        return "expression", "", ""
    if "副" in parts:
        return "adverb", "", ""
    if "名" in parts:
        return "noun", "", ""
    return "noun", "", ""


def apply_eggrolls_forms(item: dict[str, object], word: dict[str, str], pos: str, verb_class: str) -> None:
    if pos == "verb" and verb_class:
        dictionary_form = word["writing"] or word["reading"]
    elif pos == "suru_noun":
        dictionary_form = f"{word['writing'] or word['reading']}する"
        verb_class = "suru"
    else:
        return

    try:
        item["verbClass"] = verb_class
        item["verbClassLabel"] = VERB_CLASS_LABELS[verb_class]
        item["forms"] = verb_forms(dictionary_form, verb_class)
    except (KeyError, ValueError):
        item.pop("verbClass", None)
        item.pop("verbClassLabel", None)
        item.pop("forms", None)


def load_eggrolls_notes() -> dict[str, dict[str, str]]:
    if not EGGROLLS_NOTES_TSV.exists():
        return {}
    with EGGROLLS_NOTES_TSV.open(newline="", encoding="utf-8-sig") as source:
        return {
            row["NoteID"]: row
            for row in csv.DictReader(source, delimiter="\t")
            if row.get("NoteID")
        }


def load_eggrolls_imported_note_ids(words: dict[str, dict[str, str]]) -> dict[str, str]:
    if not EGGROLLS_IMPORTED_CSV.exists():
        return {}

    rows_by_level: dict[str, list[dict[str, str]]] = {level: [] for level in ("N5", "N4", "N3", "N2", "N1")}
    with EGGROLLS_IMPORTED_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            level = (row.get("level") or "").strip()
            if level in rows_by_level:
                rows_by_level[level].append(row)

    note_ids: dict[str, str] = {}
    seen_keys: set[tuple[str, str]] = set()

    for level in ("N5", "N4", "N3", "N2", "N1"):
        prefix = level.lower()
        for word_id, word in words.items():
            if word_id.startswith(f"{prefix}_") and "_egg_" not in word_id:
                seen_keys.add(word_key(word["reading"], word["writing"], word["normalizedReading"]))

        counter = 0
        for row in rows_by_level[level]:
            key = word_key(
                (row.get("reading") or "").strip(),
                (row.get("writing") or "").strip(),
                (row.get("declared") or "").strip(),
            )
            if key in seen_keys:
                continue
            counter += 1
            word_id = f"{prefix}_egg_{counter:04d}"
            if word_id in words:
                note_ids[word_id] = (row.get("note_id") or "").strip()
            seen_keys.add(key)
    return note_ids


def load_eggrolls_metadata(words: dict[str, dict[str, str]]) -> dict[str, dict[str, object]]:
    notes = load_eggrolls_notes()
    imported_note_ids = load_eggrolls_imported_note_ids(words)
    metadata: dict[str, dict[str, object]] = {}

    for word_id, note_id in imported_note_ids.items():
        if word_id not in words or note_id not in notes:
            continue
        note = notes[note_id]
        source_pos = (note.get("VocabPoS") or "").strip()
        pos, verb_class, transitivity = eggrolls_pos_config(source_pos)
        item: dict[str, object] = {
            "pos": pos,
            "posLabel": POS_LABELS[pos],
            "source": "eggrolls-JLPT10k-v3.5",
        }
        if source_pos:
            item["sourcePos"] = source_pos
        if transitivity:
            item["transitivity"] = transitivity
            item["transitivityLabel"] = TRANSITIVITY_LABELS[transitivity]

        apply_eggrolls_forms(item, words[word_id], pos, verb_class)

        if word_id.startswith("n1_"):
            example = best_eggrolls_example(note)
            if example:
                example = deepen_short_n1_example(example)
        else:
            example = first_eggrolls_example(note)
        if example:
            item["examples"] = [example]

        metadata[word_id] = item

    return metadata


def auto_meta_for_word(row: dict[str, str], examples: dict[str, dict[str, str]]) -> dict[str, object]:
    pos = infer_pos(row)
    item: dict[str, object] = {
        "pos": pos,
        "posLabel": POS_LABELS[pos],
    }
    forms = None

    if pos == "verb":
        verb_class = infer_verb_class_for_word(row)
        dictionary_form = row["writing"] or row["reading"]
        forms = verb_forms(dictionary_form, verb_class)
        item["verbClass"] = verb_class
        item["verbClassLabel"] = VERB_CLASS_LABELS[verb_class]
        item["forms"] = forms
    elif pos == "suru_noun":
        verb_class = "suru"
        dictionary_form = f"{row['writing'] or row['reading']}する"
        forms = verb_forms(dictionary_form, verb_class)
        item["verbClass"] = verb_class
        item["verbClassLabel"] = VERB_CLASS_LABELS[verb_class]
        item["forms"] = forms

    item["examples"] = [examples.get(row["id"]) or auto_example(row, pos, forms)]
    return item


def word_sort_key(word_id: str) -> tuple[str, int, int]:
    parts = word_id.split("_")
    level = parts[0]
    if len(parts) >= 3 and parts[1] == "egg":
        return level, 1, int(parts[2])
    return level, 0, int(parts[1])


def validate_headers(fieldnames: list[str] | None) -> None:
    if fieldnames != EXPECTED_FIELDS:
        raise ValueError(f"Expected CSV fields {EXPECTED_FIELDS}, got {fieldnames}")


def build_meta() -> dict[str, dict[str, object]]:
    words = load_word_index()
    examples = load_examples(words)
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
            elif pos == "suru_noun":
                dictionary_form = f"{words[word_id]['writing'] or words[word_id]['reading']}する"
                item["verbClass"] = "suru"
                item["verbClassLabel"] = VERB_CLASS_LABELS["suru"]
                item["forms"] = verb_forms(dictionary_form, "suru")
                if verb_class:
                    raise ValueError(f"Line {line_no}: suru_noun rows do not need verb_class")
            elif verb_class:
                raise ValueError(f"Line {line_no}: non-verb rows cannot set verb_class")

            if example_ja:
                item["examples"] = [{"ja": example_ja, "zh": example_zh}]
            elif word_id in examples:
                item["examples"] = [examples[word_id]]
            if note:
                item["note"] = note

            seen_ids.add(word_id)
            metadata[word_id] = item

    for word_id, item in load_eggrolls_metadata(words).items():
        metadata.setdefault(word_id, item)

    for word_id in sorted(words, key=word_sort_key):
        if not (
            word_id.startswith("n5_")
            or word_id.startswith("n4_")
            or word_id.startswith("n1_")
        ) or word_id in metadata:
            continue
        metadata[word_id] = auto_meta_for_word(words[word_id], examples)

    return dict(sorted(metadata.items(), key=lambda item: word_sort_key(item[0])))


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
