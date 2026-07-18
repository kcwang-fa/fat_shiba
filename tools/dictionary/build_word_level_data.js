const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "../..");
const WEB_DIR = path.join(ROOT, "web");
const WORD_DATA_PATH = path.join(WEB_DIR, "data/word_data.js");
const OUT_DIR = path.join(WEB_DIR, "data");
const LEVEL_ORDER = ["N5", "N4", "N3", "N2", "N1"];
const N2_BASE_WORD_ROWS = [
  ["n2_0001", "あいまい", "曖昧", "あいまい", "模糊、不明確", "kanji"],
  ["n2_0002", "あきらか", "明らか", "あきらか", "明顯、清楚", "kanji"],
  ["n2_0003", "あっとう", "圧倒", "あっとう", "壓倒、遠勝", "kanji"],
  ["n2_0004", "いじょう", "異常", "いじょう", "異常、不尋常", "kanji"],
  ["n2_0005", "いっぽう", "一方", "いっぽう", "一方面、另一方面", "kanji"],
  ["n2_0006", "いらい", "依頼", "いらい", "委託、請求、拜託", "kanji"],
  ["n2_0007", "うんえい", "運営", "うんえい", "營運、經營", "kanji"],
  ["n2_0008", "えんちょう", "延長", "えんちょう", "延長、展延", "kanji"],
  ["n2_0009", "おうぼ", "応募", "おうぼ", "報名、應徵", "kanji"],
  ["n2_0010", "かいご", "介護", "かいご", "照護、照顧", "kanji"],
  ["n2_0011", "かいさい", "開催", "かいさい", "舉辦、召開", "kanji"],
  ["n2_0012", "かくだい", "拡大", "かくだい", "擴大、放大", "kanji"],
  ["n2_0013", "かくとく", "獲得", "かくとく", "獲得、取得", "kanji"],
  ["n2_0014", "かじょう", "過剰", "かじょう", "過度、過剩", "kanji"],
  ["n2_0015", "かのうせい", "可能性", "かのうせい", "可能性", "kanji"],
  ["n2_0016", "かんり", "管理", "かんり", "管理、控管", "kanji"],
  ["n2_0017", "きたい", "期待", "きたい", "期待、期望", "kanji"],
  ["n2_0018", "きぼ", "規模", "きぼ", "規模", "kanji"],
  ["n2_0019", "きょうきゅう", "供給", "きょうきゅう", "供給、供應", "kanji"],
  ["n2_0020", "きょうちょう", "強調", "きょうちょう", "強調", "kanji"],
  ["n2_0021", "けいこう", "傾向", "けいこう", "傾向、趨勢", "kanji"],
  ["n2_0022", "けんとう", "検討", "けんとう", "檢討、研議", "kanji"],
  ["n2_0023", "こうせい", "構成", "こうせい", "構成、組成", "kanji"],
  ["n2_0024", "こうりつ", "効率", "こうりつ", "效率", "kanji"],
  ["n2_0025", "こよう", "雇用", "こよう", "雇用、聘僱", "kanji"],
  ["n2_0026", "さいよう", "採用", "さいよう", "採用、錄用；採納", "kanji"],
  ["n2_0027", "さくげん", "削減", "さくげん", "削減、刪減", "kanji"],
  ["n2_0028", "しきゅう", "支給", "しきゅう", "支給、發放", "kanji"],
  ["n2_0029", "しげん", "資源", "しげん", "資源", "kanji"],
  ["n2_0030", "しじょう", "市場", "しじょう", "市場", "kanji"],
  ["n2_0031", "じっし", "実施", "じっし", "實施、執行", "kanji"],
  ["n2_0032", "じゅよう", "需要", "じゅよう", "需求", "kanji"],
  ["n2_0033", "しょうめい", "証明", "しょうめい", "證明", "kanji"],
  ["n2_0034", "じょうしょう", "上昇", "じょうしょう", "上升、提升", "kanji"],
  ["n2_0035", "すいしん", "推進", "すいしん", "推動、推進", "kanji"],
  ["n2_0036", "せいげん", "制限", "せいげん", "限制", "kanji"],
  ["n2_0037", "せいび", "整備", "せいび", "整備、完善；維護", "kanji"],
  ["n2_0038", "せんたくし", "選択肢", "せんたくし", "選項、選擇", "kanji"],
  ["n2_0039", "そしき", "組織", "そしき", "組織", "kanji"],
  ["n2_0040", "たいしょう", "対象", "たいしょう", "對象、目標", "kanji"],
  ["n2_0041", "たっせい", "達成", "たっせい", "達成、完成", "kanji"],
  ["n2_0042", "ちいき", "地域", "ちいき", "地區、區域", "kanji"],
  ["n2_0043", "ちょうせい", "調整", "ちょうせい", "調整", "kanji"],
  ["n2_0044", "てきよう", "適用", "てきよう", "適用、套用", "kanji"],
  ["n2_0045", "とうし", "投資", "とうし", "投資", "kanji"],
  ["n2_0046", "どうにゅう", "導入", "どうにゅう", "導入、引進", "kanji"],
  ["n2_0047", "はんえい", "反映", "はんえい", "反映、反應出", "kanji"],
  ["n2_0048", "ひょうげん", "表現", "ひょうげん", "表現、表達", "kanji"],
  ["n2_0049", "ふきゅう", "普及", "ふきゅう", "普及、推廣", "kanji"],
  ["n2_0050", "ぶんせき", "分析", "ぶんせき", "分析", "kanji"],
  ["n2_0051", "へんこう", "変更", "へんこう", "變更、更改", "kanji"],
  ["n2_0052", "ほしょう", "保証", "ほしょう", "保證、擔保", "kanji"],
  ["n2_0053", "みなおし", "見直し", "みなおし", "重新檢視、重新評估", "kanji"],
  ["n2_0054", "ゆうせん", "優先", "ゆうせん", "優先", "kanji"],
  ["n2_0055", "ようきゅう", "要求", "ようきゅう", "要求、請求", "kanji"],
  ["n2_0056", "りろん", "理論", "りろん", "理論", "kanji"]
];

function loadRawWordData() {
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(WORD_DATA_PATH, "utf8"), sandbox, {
    filename: WORD_DATA_PATH
  });
  return sandbox.window.FAT_SHIBA_WORD_DATA;
}

function toHiraganaKana(char) {
  const code = char.charCodeAt(0);
  if (code >= 0x30A1 && code <= 0x30F6) return String.fromCharCode(code - 0x60);
  return char;
}

function kanaVowel(kana) {
  const normalizedKana = toHiraganaKana(kana);
  const vowels = {
    あ: "a", か: "a", が: "a", さ: "a", ざ: "a", た: "a", だ: "a", な: "a", は: "a", ば: "a", ぱ: "a", ま: "a", や: "a", ゃ: "a", ら: "a", わ: "a",
    い: "i", き: "i", ぎ: "i", し: "i", じ: "i", ち: "i", ぢ: "i", に: "i", ひ: "i", び: "i", ぴ: "i", み: "i", り: "i",
    う: "u", く: "u", ぐ: "u", す: "u", ず: "u", つ: "u", づ: "u", ぬ: "u", ふ: "u", ぶ: "u", ぷ: "u", む: "u", ゆ: "u", ゅ: "u", る: "u",
    え: "e", け: "e", げ: "e", せ: "e", ぜ: "e", て: "e", で: "e", ね: "e", へ: "e", べ: "e", ぺ: "e", め: "e", れ: "e",
    お: "o", こ: "o", ご: "o", そ: "o", ぞ: "o", と: "o", ど: "o", の: "o", ほ: "o", ぼ: "o", ぽ: "o", も: "o", よ: "o", ょ: "o", ろ: "o", を: "o"
  };
  return vowels[normalizedKana] || "";
}

function longVowelKana(previousKana) {
  const vowel = kanaVowel(previousKana);
  return { a: "あ", i: "い", u: "う", e: "え", o: "お" }[vowel] || "";
}

function normalizeKanaReading(value) {
  const text = String(value || "").trim().normalize("NFKC");
  const output = [];

  for (const rawChar of Array.from(text)) {
    const kana = toHiraganaKana(rawChar);
    if (kana === "ー") {
      const longKana = longVowelKana(output[output.length - 1]);
      if (longKana) output.push(longKana);
      continue;
    }
    output.push(kana);
  }

  return output.join("");
}

function normalizeDisplayReading(value) {
  return String(value || "").trim().normalize("NFKC");
}

function playableReadingForWord(reading, declaredNormalizedReading, script) {
  return script === "katakana"
    ? normalizeDisplayReading(reading || declaredNormalizedReading)
    : normalizeKanaReading(reading || declaredNormalizedReading);
}

function buildLevelWordRows(prefix, startNumber, rows, excludedReadings = new Set(), limit = Infinity) {
  const seenReadings = new Set(excludedReadings);
  return String(rows || "").trim().split("\n").map((row) => row.trim()).filter(Boolean).reduce((list, row) => {
    if (list.length >= limit) return list;
    const parts = row.split("|").map((part) => part.trim());
    if (parts.length !== 5) {
      throw new Error(`Invalid ${prefix} word row: ${row}`);
    }
    const [reading, writing, declaredNormalizedReading, zh, script] = parts;
    const normalizedReading = normalizeKanaReading(reading || declaredNormalizedReading);
    if (seenReadings.has(normalizedReading)) return list;
    seenReadings.add(normalizedReading);
    list.push([
      `${prefix}_${String(startNumber + list.length).padStart(4, "0")}`,
      reading,
      writing,
      normalizedReading,
      zh,
      script
    ]);
    return list;
  }, []);
}

function wordKeyForParts(reading, writing, declaredNormalizedReading) {
  return `${normalizeKanaReading(reading || declaredNormalizedReading)}\u0000${normalizeDisplayReading(writing)}`;
}

function wordKeyForRow(row) {
  return wordKeyForParts(row[1], row[2], row[3]);
}

function buildImportedWordRows(prefix, rows, excludedKeys = new Set()) {
  const seenKeys = new Set(excludedKeys);
  return String(rows || "").trim().split("\n").map((row) => row.trim()).filter(Boolean).reduce((list, row) => {
    const parts = row.split("|").map((part) => part.trim());
    if (parts.length !== 5) {
      throw new Error(`Invalid ${prefix} imported word row: ${row}`);
    }
    const [reading, writing, declaredNormalizedReading, zh, script] = parts;
    const normalizedReading = normalizeKanaReading(reading || declaredNormalizedReading);
    const key = wordKeyForParts(reading, writing, declaredNormalizedReading);
    if (seenKeys.has(key)) return list;
    seenKeys.add(key);
    list.push([
      `${prefix}_${String(list.length + 1).padStart(4, "0")}`,
      reading,
      writing,
      normalizedReading,
      zh,
      script
    ]);
    return list;
  }, []);
}

function uniqueFirstWordByReadingAndWriting(words) {
  const seen = new Set();
  return words.filter((word) => {
    const key = `${word.playReading}\u0000${word.writing}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function isPlayableWord(word) {
  return Boolean(word.playReading);
}

function buildWordsByLevel(data, n2BaseRows) {
  const {
    RAW_WORDS,
    N4_BASE_WORD_ROWS,
    N4_EXTRA_WORD_ROWS_TEXT,
    N4_CSV_WORD_ROWS_TEXT,
    N3_BASE_WORD_ROWS,
    N3_RESERVED_UPPER_LEVEL_READING_VALUES,
    N3_EXTRA_WORD_ROWS_TEXT,
    N2_EXTRA_WORD_ROWS_TEXT,
    N1_BASE_WORD_ROWS,
    N1_EXTRA_WORD_ROWS_TEXT,
    EGGROLLS_N5_WORD_ROWS_TEXT,
    EGGROLLS_N4_WORD_ROWS_TEXT,
    EGGROLLS_N3_WORD_ROWS_TEXT,
    EGGROLLS_N2_WORD_ROWS_TEXT,
    EGGROLLS_N1_WORD_ROWS_TEXT
  } = data;

  const N4_BASE_READINGS = new Set(N4_BASE_WORD_ROWS.map((row) => normalizeKanaReading(row[1] || row[3])));
  const N5_WORD_READINGS = new Set(RAW_WORDS.map((row) => normalizeKanaReading(row[1] || row[3])));
  const N4_EXTRA_WORD_ROWS = buildLevelWordRows("n4", 61, N4_EXTRA_WORD_ROWS_TEXT, new Set([...N5_WORD_READINGS, ...N4_BASE_READINGS]), 540);
  const N4_CSV_WORD_ROWS = buildLevelWordRows("n4", 601, N4_CSV_WORD_ROWS_TEXT, new Set([
    ...N5_WORD_READINGS,
    ...N4_BASE_READINGS,
    ...N4_EXTRA_WORD_ROWS.map((row) => normalizeKanaReading(row[1] || row[3]))
  ]));
  const N3_LOWER_LEVEL_READINGS = new Set([
    ...N5_WORD_READINGS,
    ...N4_BASE_READINGS,
    ...N4_EXTRA_WORD_ROWS.map((row) => normalizeKanaReading(row[1] || row[3]))
  ]);
  const N3_BASE_READINGS = new Set(N3_BASE_WORD_ROWS.map((row) => normalizeKanaReading(row[1] || row[3])));
  const N3_RESERVED_UPPER_LEVEL_READINGS = new Set(N3_RESERVED_UPPER_LEVEL_READING_VALUES.map(normalizeKanaReading));
  const N3_EXTRA_WORD_ROWS = buildLevelWordRows("n3", 61, N3_EXTRA_WORD_ROWS_TEXT, new Set([...N3_LOWER_LEVEL_READINGS, ...N3_BASE_READINGS, ...N3_RESERVED_UPPER_LEVEL_READINGS]));
  const N4_WORD_ROWS = [
    ...N4_BASE_WORD_ROWS,
    ...N4_EXTRA_WORD_ROWS,
    ...N4_CSV_WORD_ROWS
  ].filter((row) => {
    const normalizedReading = normalizeKanaReading(row[1] || row[3]);
    return !N5_WORD_READINGS.has(normalizedReading) && !(normalizedReading === "いっぽう" && row[2] === "一方");
  });
  const N3_WORD_ROWS = [
    ...N3_BASE_WORD_ROWS,
    ...N3_EXTRA_WORD_ROWS
  ].filter((row) => !N3_LOWER_LEVEL_READINGS.has(normalizeKanaReading(row[1] || row[3])));
  const N2_LOWER_LEVEL_READINGS = new Set([
    ...RAW_WORDS,
    ...N4_WORD_ROWS,
    ...N3_WORD_ROWS
  ].map((row) => normalizeKanaReading(row[1] || row[3])));
  const N2_BASE_READINGS = new Set(n2BaseRows.map((row) => normalizeKanaReading(row[1] || row[3])));
  const N2_EXTRA_WORD_ROWS = buildLevelWordRows("n2", 57, N2_EXTRA_WORD_ROWS_TEXT, new Set([...N2_LOWER_LEVEL_READINGS, ...N2_BASE_READINGS]));
  const N1_LOWER_LEVEL_READINGS = new Set([
    ...RAW_WORDS,
    ...N4_WORD_ROWS,
    ...N3_WORD_ROWS,
    ...n2BaseRows,
    ...N2_EXTRA_WORD_ROWS
  ].map((row) => normalizeKanaReading(row[1] || row[3])));
  const N1_BASE_READINGS = new Set(N1_BASE_WORD_ROWS.map((row) => normalizeKanaReading(row[1] || row[3])));
  const N1_EXTRA_WORD_ROWS = buildLevelWordRows("n1", 51, N1_EXTRA_WORD_ROWS_TEXT, new Set([...N1_LOWER_LEVEL_READINGS, ...N1_BASE_READINGS]));
  const N5_EGGROLLS_WORD_ROWS = buildImportedWordRows("n5_egg", EGGROLLS_N5_WORD_ROWS_TEXT, new Set(RAW_WORDS.map(wordKeyForRow)));
  const N4_EGGROLLS_WORD_ROWS = buildImportedWordRows("n4_egg", EGGROLLS_N4_WORD_ROWS_TEXT, new Set([
    ...RAW_WORDS,
    ...N5_EGGROLLS_WORD_ROWS,
    ...N4_WORD_ROWS
  ].map(wordKeyForRow)));
  const N3_EGGROLLS_WORD_ROWS = buildImportedWordRows("n3_egg", EGGROLLS_N3_WORD_ROWS_TEXT, new Set([
    ...RAW_WORDS,
    ...N5_EGGROLLS_WORD_ROWS,
    ...N4_WORD_ROWS,
    ...N4_EGGROLLS_WORD_ROWS,
    ...N3_WORD_ROWS
  ].map(wordKeyForRow)));
  const N2_EGGROLLS_WORD_ROWS = buildImportedWordRows("n2_egg", EGGROLLS_N2_WORD_ROWS_TEXT, new Set([
    ...RAW_WORDS,
    ...N5_EGGROLLS_WORD_ROWS,
    ...N4_WORD_ROWS,
    ...N4_EGGROLLS_WORD_ROWS,
    ...N3_WORD_ROWS,
    ...N3_EGGROLLS_WORD_ROWS,
    ...n2BaseRows,
    ...N2_EXTRA_WORD_ROWS
  ].map(wordKeyForRow)));
  const N1_EGGROLLS_WORD_ROWS = buildImportedWordRows("n1_egg", EGGROLLS_N1_WORD_ROWS_TEXT, new Set([
    ...RAW_WORDS,
    ...N5_EGGROLLS_WORD_ROWS,
    ...N4_WORD_ROWS,
    ...N4_EGGROLLS_WORD_ROWS,
    ...N3_WORD_ROWS,
    ...N3_EGGROLLS_WORD_ROWS,
    ...n2BaseRows,
    ...N2_EXTRA_WORD_ROWS,
    ...N2_EGGROLLS_WORD_ROWS,
    ...N1_BASE_WORD_ROWS,
    ...N1_EXTRA_WORD_ROWS
  ].map(wordKeyForRow)));

  const rowsByLevel = {
    N5: [
      ...RAW_WORDS,
      ...N5_EGGROLLS_WORD_ROWS
    ],
    N4: [
      ...N4_WORD_ROWS,
      ...N4_EGGROLLS_WORD_ROWS
    ],
    N3: [
      ...N3_WORD_ROWS,
      ...N3_EGGROLLS_WORD_ROWS
    ],
    N2: [
      ...n2BaseRows,
      ...N2_EXTRA_WORD_ROWS,
      ...N2_EGGROLLS_WORD_ROWS
    ],
    N1: [
      ...N1_BASE_WORD_ROWS,
      ...N1_EXTRA_WORD_ROWS,
      ...N1_EGGROLLS_WORD_ROWS
    ]
  };

  const allWords = uniqueFirstWordByReadingAndWriting(LEVEL_ORDER.flatMap((level) =>
    rowsByLevel[level].map(([id, reading, writing, declaredNormalizedReading, zh, script]) => {
      const normalizedReading = normalizeKanaReading(reading || declaredNormalizedReading);
      const playReading = playableReadingForWord(reading, declaredNormalizedReading, script);
      return {
        id,
        reading,
        writing,
        normalizedReading,
        playReading,
        zh,
        level,
        script
      };
    })
  ).filter(isPlayableWord));

  return LEVEL_ORDER.reduce((map, level) => {
    map[level] = allWords.filter((word) => word.level === level);
    return map;
  }, {});
}

function writeLevelFile(level, words) {
  const fileName = `word-level-${level.toLowerCase()}.js`;
  const output = [
    "// Generated by tools/dictionary/build_word_level_data.js. Do not edit by hand.",
    "window.FAT_SHIBA_WORD_LEVELS = window.FAT_SHIBA_WORD_LEVELS || {};",
    `window.FAT_SHIBA_WORD_LEVELS.${level} = ${JSON.stringify(words)};`,
    ""
  ].join("\n");
  fs.writeFileSync(path.join(OUT_DIR, fileName), output);
}

function main() {
  const data = loadRawWordData();
  const wordsByLevel = buildWordsByLevel(data, N2_BASE_WORD_ROWS);

  for (const level of LEVEL_ORDER) {
    writeLevelFile(level, wordsByLevel[level]);
  }

  const counts = LEVEL_ORDER.map((level) => `${level}:${wordsByLevel[level].length}`).join(" ");
  console.log(`Generated word level data: ${counts}`);
}

main();
