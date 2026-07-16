#!/usr/bin/env python3
"""Fill N3 Chinese clues from OCR candidate context.

The corrected N3 CSV only has reading/writing columns.  The raw candidate CSV
still contains the OCR context around each entry, including the book's Chinese
gloss.  This script extracts a conservative gloss, writes an override table,
updates the cleaned game CSV, and refreshes the N3 rows in word_data.js.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

from merge_n3_csv_wordlist import (
    DATA_PATH,
    N3_BLOCK_END,
    N3_BLOCK_START,
    READING_CORRECTIONS,
    TOOL_ROOT,
    WRITING_CORRECTIONS,
    escape_pipe,
    extract_word_text_property,
    normalize_kana_reading,
    replace_between,
)


CANDIDATES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_candidates.csv"
CLEANED_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_wordlist_cleaned_for_game.csv"
OVERRIDES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_zh_overrides.csv"
MANUAL_OVERRIDES_CSV = TOOL_ROOT / "dictionary" / "jlpt_n3_zh_manual_overrides.csv"

JAPANESE_KANA_RE = re.compile(r"[ぁ-んァ-ヶー]")
CJK_RE = re.compile(r"[一-龯々]")
ENTRY_MARKER_RE = re.compile(r"^\s*[|｜]?\s*[oO]?\d{0,2}\s*[|｜]\s*")
EXAMPLE_MARKER_RE = re.compile(r"[圏団図国較譯訳讓護謂詞舞属避聞]\s*[ぁ-んァ-ヶー一-龯々]")
LEADING_POS_RE = re.compile(
    r"^(?:名|自|他|五|一|形動|副|感|代|接尾|漢造|連体|連語|助|接|形|生|多|全|人|る|"
    r"名[・.、:]?|自サ|他サ|名・自サ|名・他サ|名・他サ・自サ|名・形動|名・副|"
    r"@|宮|秘|包|色|久|負|念|創|軸|祁天|敘|說還|ご|富2|上人|枉==)+[)）・.、:：\\s-]*"
)

TRADITIONAL_REPLACEMENTS = {
    "台": "臺",
    "众": "眾",
    "体": "體",
    "价": "價",
    "会": "會",
    "传": "傳",
    "伤": "傷",
    "关": "關",
    "兴": "興",
    "冲": "衝",
    "净": "淨",
    "况": "況",
    "决": "決",
    "划": "劃",
    "剂": "劑",
    "动": "動",
    "区": "區",
    "医": "醫",
    "华": "華",
    "单": "單",
    "压": "壓",
    "厅": "廳",
    "发": "發",
    "变": "變",
    "叶": "葉",
    "号": "號",
    "听": "聽",
    "员": "員",
    "响": "響",
    "国": "國",
    "围": "圍",
    "场": "場",
    "块": "塊",
    "坏": "壞",
    "声": "聲",
    "处": "處",
    "备": "備",
    "复": "復",
    "头": "頭",
    "实": "實",
    "对": "對",
    "导": "導",
    "层": "層",
    "岁": "歲",
    "师": "師",
    "废": "廢",
    "开": "開",
    "张": "張",
    "强": "強",
    "归": "歸",
    "当": "當",
    "录": "錄",
    "径": "徑",
    "从": "從",
    "态": "態",
    "总": "總",
    "恶": "惡",
    "惯": "慣",
    "应": "應",
    "戏": "戲",
    "户": "戶",
    "扫": "掃",
    "扩": "擴",
    "担": "擔",
    "拥": "擁",
    "择": "擇",
    "换": "換",
    "据": "據",
    "损": "損",
    "报": "報",
    "摄": "攝",
    "数": "數",
    "断": "斷",
    "旧": "舊",
    "时": "時",
    "显": "顯",
    "杂": "雜",
    "权": "權",
    "条": "條",
    "来": "來",
    "极": "極",
    "构": "構",
    "样": "樣",
    "标": "標",
    "检": "檢",
    "楼": "樓",
    "欢": "歡",
    "欧": "歐",
    "残": "殘",
    "气": "氣",
    "汇": "匯",
    "汉": "漢",
    "测": "測",
    "济": "濟",
    "浓": "濃",
    "湿": "濕",
    "灯": "燈",
    "灵": "靈",
    "炉": "爐",
    "点": "點",
    "烦": "煩",
    "热": "熱",
    "爱": "愛",
    "状": "狀",
    "独": "獨",
    "现": "現",
    "环": "環",
    "画": "畫",
    "疗": "療",
    "盐": "鹽",
    "监": "監",
    "盖": "蓋",
    "礼": "禮",
    "离": "離",
    "种": "種",
    "积": "積",
    "称": "稱",
    "稳": "穩",
    "穷": "窮",
    "竞": "競",
    "类": "類",
    "练": "練",
    "经": "經",
    "结": "結",
    "给": "給",
    "统": "統",
    "续": "續",
    "绿": "綠",
    "维": "維",
    "罚": "罰",
    "职": "職",
    "联": "聯",
    "脑": "腦",
    "艺": "藝",
    "节": "節",
    "苏": "蘇",
    "药": "藥",
    "观": "觀",
    "规": "規",
    "视": "視",
    "觉": "覺",
    "议": "議",
    "论": "論",
    "设": "設",
    "识": "識",
    "词": "詞",
    "译": "譯",
    "证": "證",
    "评": "評",
    "试": "試",
    "话": "話",
    "请": "請",
    "调": "調",
    "负": "負",
    "财": "財",
    "货": "貨",
    "质": "質",
    "费": "費",
    "资": "資",
    "赛": "賽",
    "赞": "贊",
    "赵": "趙",
    "车": "車",
    "转": "轉",
    "轻": "輕",
    "较": "較",
    "边": "邊",
    "达": "達",
    "过": "過",
    "运": "運",
    "还": "還",
    "进": "進",
    "远": "遠",
    "连": "連",
    "迟": "遲",
    "选": "選",
    "递": "遞",
    "适": "適",
    "遗": "遺",
    "邮": "郵",
    "邻": "鄰",
    "释": "釋",
    "钢": "鋼",
    "铁": "鐵",
    "长": "長",
    "门": "門",
    "间": "間",
    "队": "隊",
    "阶": "階",
    "际": "際",
    "难": "難",
    "电": "電",
    "面": "麵",
    "须": "須",
    "预": "預",
    "领": "領",
    "频": "頻",
    "题": "題",
    "额": "額",
    "风": "風",
    "饭": "飯",
    "馆": "館",
    "驱": "驅",
    "验": "驗",
    "驿": "驛",
    "鱼": "魚",
    "鲜": "鮮",
}

MANUAL_OVERRIDES = {
    "あっというまに": "一眨眼的功夫",
    "おくれ": "落後、遲延",
    "ぎりぎり": "最大限度、極限",
    "こうはん": "後半、後一半",
    "しょうご": "正午",
    "しんや": "深夜",
    "せいき": "世紀、時代、年代",
    "ぜんはん": "前半、前半部",
    "そうちょう": "早晨、清晨",
    "ちこく": "遲到",
    "どうじに": "同時、馬上",
    "ふける": "夜深",
    "ぶり": "相隔",
    "やかん": "夜間",
    "しゅう": "週、星期、一圈",
    "うむ": "生、產生",
    "しゃっくり": "打嗝",
    "こる": "凝固、入迷、講究",
    "くずす": "拆毀、打亂",
    "くむ": "打水、汲取",
    "けいたい": "攜帶、手機",
    "じゅみょう": "壽命、耐用期限",
    "ゆうらんせん": "遊覽船",
    "ほそう": "鋪路",
    "じょうようしゃ": "自小客車",
    "つうこう": "通行、往來",
    "へこむ": "凹陷、屈服、虧空",
    "カープ": "彎道、曲線",
    "ガム": "口香糖",
    "ビール": "啤酒",
    "シーズン": "季節、時期",
    "スープ": "湯",
    "オーバーコート": "大衣、外套",
    "スニーカー": "運動鞋",
    "ボランティア": "志工、義工",
    "ラッシュ": "尖峰時段、擁擠",
    "トラック": "卡車、跑道",
    "アニメ": "動畫",
    "エスエフ": "科幻",
    "ホラー": "恐怖作品",
    "カード": "卡片",
    "プリペイドカード": "預付卡",
    "バイバイ": "再見",
    "ウィスキー": "威士忌",
    "コンクリート": "混凝土",
    "ロビー": "大廳",
    "トンネル": "隧道",
    "ヘリコプター": "直升機",
    "エネルギー": "能源、精力",
    "プラスチック": "塑膠",
    "ビルディング": "大樓、建築物",
    "パンク": "爆胎、破裂",
    "カー": "車、汽車",
    "カーブ": "彎道、曲線",
    "カープ": "彎道、曲線",
    "ランチ": "午餐",
    "デザート": "甜點、餐後點心",
    "ティーシャツ": "T恤",
    "バンド": "樂團、帶子",
    "プロ": "專業人士、職業選手",
    "リビング": "客廳、起居室",
    "ジャケット": "夾克、外套",
    "ファストフード": "速食",
    "デザイン": "設計、圖案",
    "ソース": "醬汁",
    "ケチャップ": "番茄醬",
    "バイオリン": "小提琴",
    "セット": "一組、一套",
}


def nfkc(value: str | None) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip())


def to_traditional(value: str) -> str:
    return "".join(TRADITIONAL_REPLACEMENTS.get(char, char) for char in value)


def normalize_entry_no(value: str | None) -> str:
    value = nfkc(value).lower().replace("o", "0")
    return value.zfill(2) if value.isdigit() else value


def normalize_lookup_reading(value: str) -> str:
    value = nfkc(value)
    value = re.sub(r"\s+", "", value)
    value = value.strip(" |:;。・,，.「」『』[]【】")
    value = READING_CORRECTIONS.get(value, value)
    return normalize_kana_reading(value)


def cleanup_gloss(value: str) -> str:
    value = nfkc(value)
    if re.search(r"\d{3}\s*[|｜]", value):
        return ""
    value = re.sub(r"^[^、，,;；:：]{1,12}[)）]", "", value)
    value = value.replace("ヽ", "、").replace("・", "、").replace(";", "、").replace("；", "、")
    value = value.replace(",", "、").replace("，", "、").replace(":", "、").replace("：", "、")
    value = re.sub(r"\([^)]{0,12}\)", "", value)
    value = re.sub(r"（[^）]{0,12}）", "", value)
    value = value.replace("(", "、").replace(")", "")
    value = re.sub(r"[A-Za-z0-9N]+", "", value)
    value = re.sub(r"[\|｜【】「」『』\[\]{}<>~^_@#$=+*/\\`]", "", value)
    value = re.sub(r"[ぁ-んァ-ヶー]+", "", value)
    value = LEADING_POS_RE.sub("", value)
    value = re.sub(
        r"^(?:包|和|全|分|人|介|當人|身他|本六|所自功|額|創|公|急|圓|暑|"
        r"名馬|失帯|會|下|上|秘|名|自|他|自他|他、自)\s+",
        "",
        value,
    )
    value = re.sub(r"^[^一-龯々]+", "", value)
    value = re.sub(r"[\s\u3000'\"“”]+", "", value)
    value = re.sub(r"、{2,}", "、", value)
    value = value.strip(" 、。.!！?？-")
    value = to_traditional(value)
    value = value.replace("麵前", "面前")
    return value


def is_useful_gloss(value: str, writing: str) -> bool:
    if not value or not CJK_RE.search(value):
        return False
    if len(value) < 2:
        return False
    if value in {"時間", "時候", "季節", "交通", "家具", "工具"}:
        return False
    if writing and value == writing and len(value) <= 2:
        return False
    return True


def extract_context_gloss(context: str, writing: str) -> str:
    context = nfkc(context)
    if "】" in context:
        context = context.split("】", 1)[1]
    elif "/" in context:
        context = context.split("/", 1)[1]

    pieces: list[str] = []
    for raw_part in context.split("/"):
        if re.search(r"\d{3}\s*[|｜]", raw_part):
            break
        part = ENTRY_MARKER_RE.sub("", raw_part)
        marker_match = EXAMPLE_MARKER_RE.search(part)
        if marker_match:
            part = part[: marker_match.start()]
        part = cleanup_gloss(part)
        if is_useful_gloss(part, writing):
            pieces.append(part)
        if len("、".join(pieces)) >= 24:
            break

    gloss = "、".join(pieces)
    gloss = re.sub(r"、{2,}", "、", gloss).strip("、")
    if len(gloss) > 36:
        gloss = gloss[:36].rstrip("、")
    return gloss


def candidate_lookup() -> dict[tuple[str, str, str, str], str]:
    lookup: dict[tuple[str, str, str, str], str] = {}
    with CANDIDATES_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            reading_key = normalize_lookup_reading(row.get("headword", ""))
            page = nfkc(row.get("page", ""))
            column = nfkc(row.get("column", ""))
            entry_no = normalize_entry_no(row.get("entry_no", ""))
            context = nfkc(row.get("ocr_context", ""))
            if not reading_key or not context:
                continue
            lookup[(page, column, entry_no, reading_key)] = context
            lookup.setdefault((page, column, "", reading_key), context)
    return lookup


def load_manual_overrides() -> dict[str, str]:
    overrides: dict[str, str] = {}
    if not MANUAL_OVERRIDES_CSV.exists():
        return overrides

    with MANUAL_OVERRIDES_CSV.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            key = nfkc(row.get("declaredNormalizedReading"))
            zh = nfkc(row.get("zh"))
            if key and zh:
                overrides[normalize_kana_reading(key)] = zh
    return overrides


def context_for_row(row: dict[str, str], lookup: dict[tuple[str, str, str, str], str]) -> str:
    normalized = nfkc(row["declaredNormalizedReading"])
    page = nfkc(row.get("source_page", ""))
    column = nfkc(row.get("source_column", ""))
    entry_no = normalize_entry_no(row.get("source_entry_no", ""))
    return lookup.get((page, column, entry_no, normalized), "") or lookup.get((page, column, "", normalized), "")


def build_overrides() -> tuple[dict[str, str], Counter[str]]:
    lookup = candidate_lookup()
    manual_overrides = load_manual_overrides()
    overrides: dict[str, str] = {}
    stats: Counter[str] = Counter()

    with CLEANED_CSV.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))

    for row in rows:
        normalized = nfkc(row["declaredNormalizedReading"])
        manual = (
            manual_overrides.get(normalized)
            or MANUAL_OVERRIDES.get(normalized)
            or MANUAL_OVERRIDES.get(nfkc(row.get("reading")))
            or MANUAL_OVERRIDES.get(nfkc(row.get("writing")))
            or MANUAL_OVERRIDES.get(nfkc(row.get("source_writing")))
        )
        if manual:
            overrides[normalized] = manual
            stats["manual"] += 1
            continue

        context = context_for_row(row, lookup)
        gloss = extract_context_gloss(context, row.get("source_writing") or row.get("writing", ""))
        if gloss:
            overrides[normalized] = gloss
            stats["ocr_context"] += 1
        else:
            stats["fallback"] += 1

    return overrides, stats


def update_cleaned_csv(overrides: dict[str, str]) -> tuple[int, int, dict[str, str]]:
    with CLEANED_CSV.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    changed = 0
    desired_zh: dict[str, str] = {}
    for row in rows:
        normalized = nfkc(row["declaredNormalizedReading"])
        target = overrides.get(normalized) or nfkc(row.get("source_writing")) or nfkc(row.get("writing"))
        desired_zh[normalized] = target
        if target and row.get("zh") != target:
            row["zh"] = target
            changed += 1

    with CLEANED_CSV.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), changed, desired_zh


def update_word_data(desired_zh: dict[str, str]) -> int:
    word_data = DATA_PATH.read_text(encoding="utf-8")
    text = extract_word_text_property(word_data, "N3_EXTRA_WORD_ROWS_TEXT")
    updated_lines: list[str] = []
    changed = 0

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) > 5:
            parts = parts[:3] + ["／".join(parts[3:-1])] + [parts[-1]]
        if len(parts) != 5:
            raise ValueError(f"Invalid N3 word row: {line}")
        normalized = nfkc(parts[2])
        target = desired_zh.get(normalized)
        if target and parts[3] != target:
            parts[3] = target
            changed += 1
        updated_lines.append("|".join(escape_pipe(part) for part in parts))

    replacement = f"{N3_BLOCK_START}\n\n" + "\n".join(updated_lines) + f"\n{N3_BLOCK_END}"
    DATA_PATH.write_text(replace_between(word_data, N3_BLOCK_START, N3_BLOCK_END, replacement), encoding="utf-8")
    return changed


def write_overrides(overrides: dict[str, str]) -> None:
    with CLEANED_CSV.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))

    with OVERRIDES_CSV.open("w", newline="", encoding="utf-8") as output:
        fields = ["declaredNormalizedReading", "reading", "writing", "zh", "source_page", "source_column", "source_entry_no"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            normalized = nfkc(row["declaredNormalizedReading"])
            zh = overrides.get(normalized)
            if not zh:
                continue
            writer.writerow(
                {
                    "declaredNormalizedReading": normalized,
                    "reading": row["reading"],
                    "writing": row["writing"],
                    "zh": zh,
                    "source_page": row["source_page"],
                    "source_column": row["source_column"],
                    "source_entry_no": row["source_entry_no"],
                }
            )


def main() -> None:
    overrides, stats = build_overrides()
    write_overrides(overrides)
    cleaned_total, cleaned_changed, desired_zh = update_cleaned_csv(overrides)
    word_data_changed = update_word_data(desired_zh)

    print(f"overrides={len(overrides)}")
    print(f"cleaned_rows={cleaned_total}")
    print(f"cleaned_changed={cleaned_changed}")
    print(f"word_data_changed={word_data_changed}")
    for key, count in sorted(stats.items()):
        print(f"{key}={count}")
    print(f"output={OVERRIDES_CSV}")


if __name__ == "__main__":
    main()
