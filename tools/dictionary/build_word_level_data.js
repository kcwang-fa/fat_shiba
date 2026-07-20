const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const OUT_DIR = path.join(ROOT, "web/data");
const SOURCE_WORD_DIR = path.join(ROOT, "tools/dictionary/sources/words");
// 每個等級可各自有一份人工排除清單 n{level}_review.csv（如 n3_review.csv、n2_review.csv）。
// 檔案存在才會被讀取，所以未來要加 n1_review.csv 直接放檔案就生效，不用改程式。
const REVIEW_CSV_DIR = path.join(ROOT, "tools/dictionary");
const LEVEL_ORDER = ["N5", "N4", "N3", "N2", "N1"];
const REQUIRED_FIELDS = ["id", "reading", "writing", "normalizedReading", "playReading", "zh", "level", "script"];

function parseCsvRecords(text, filePath) {
  const records = [];
  let values = [];
  let value = "";
  let inQuotes = false;
  let fieldQuoted = false;
  let lineNumber = 1;
  let recordLineNumber = 1;

  function finishField() {
    values.push(value);
    value = "";
    fieldQuoted = false;
  }

  function finishRecord() {
    const recordHadQuotedField = fieldQuoted;
    finishField();
    if (values.length > 1 || values[0] !== "" || recordHadQuotedField) {
      records.push({ values, lineNumber: recordLineNumber });
    }
    values = [];
    recordLineNumber = lineNumber + 1;
  }

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"' && inQuotes && next === '"') {
      value += '"';
      index += 1;
      continue;
    }
    if (char === '"') {
      inQuotes = !inQuotes;
      fieldQuoted = true;
      continue;
    }
    if (char === "," && !inQuotes) {
      finishField();
      continue;
    }
    if ((char === "\n" || char === "\r") && !inQuotes) {
      finishRecord();
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      lineNumber += 1;
      continue;
    }
    if (char === "\n") {
      lineNumber += 1;
    }
    value += char;
  }

  if (inQuotes) throw new Error(`${filePath}:${recordLineNumber} has an unclosed CSV quote`);
  if (value || values.length || fieldQuoted) {
    finishRecord();
  }
  return records;
}

function readCsvRows(filePath, requiredFields = REQUIRED_FIELDS) {
  const text = fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
  if (!text) return [];

  const records = parseCsvRecords(text, filePath);
  if (!records.length) return [];

  const [{ values: headers }, ...rows] = records;
  for (const field of requiredFields) {
    if (!headers.includes(field)) {
      throw new Error(`${filePath} is missing required field ${field}`);
    }
  }

  return rows.map((record) => {
    const { values, lineNumber } = record;
    if (values.length !== headers.length) {
      throw new Error(`${filePath}:${lineNumber} expected ${headers.length} fields, got ${values.length}`);
    }
    return headers.reduce((row, header, valueIndex) => {
      row[header] = values[valueIndex] || "";
      return row;
    }, {
      __sourceFile: path.relative(ROOT, filePath),
      __lineNumber: lineNumber
    });
  });
}

function wordFileNamesForLevel(level) {
  const prefix = level.toLowerCase();
  return [`${prefix}_core.csv`, `${prefix}_eggrolls.csv`];
}

function loadReviewIdsForLevel(level) {
  // 例如 level="N3" 對到 tools/dictionary/n3_review.csv。
  const reviewCsvPath = path.join(REVIEW_CSV_DIR, `${level.toLowerCase()}_review.csv`);
  if (!fs.existsSync(reviewCsvPath)) return new Set();
  return new Set(
    readCsvRows(reviewCsvPath, ["id"])
      .map((row) => String(row.id || "").trim())
      .filter(Boolean)
  );
}

function normalizeSourceWord(row, expectedLevel, fileName) {
  const word = REQUIRED_FIELDS.reduce((item, field) => {
    item[field] = String(row[field] || "").trim();
    return item;
  }, {});
  word.__sourceFile = row.__sourceFile;
  word.__lineNumber = row.__lineNumber;

  if (!word.id) throw new Error(`${fileName}: word id is required`);
  if (word.level !== expectedLevel) {
    throw new Error(`${fileName}: ${word.id} has level ${word.level}, expected ${expectedLevel}`);
  }
  if (!word.playReading) throw new Error(`${fileName}: ${word.id} is missing playReading`);

  return word;
}

function uniqueFirstWordByReadingAndWriting(words) {
  const seen = new Set();
  const keptByKey = new Map();
  return words.filter((word) => {
    const key = `${word.playReading}\u0000${word.writing}`;
    if (seen.has(key)) {
      const keptWord = keptByKey.get(key);
      console.warn(
        `warning: deduplicated ${word.__sourceFile}:${word.__lineNumber} ${word.id}; ` +
        `kept ${keptWord.__sourceFile}:${keptWord.__lineNumber} ${keptWord.id} ` +
        `for ${word.playReading} / ${word.writing}`
      );
      return false;
    }
    seen.add(key);
    keptByKey.set(key, word);
    return true;
  });
}

function loadWordsByLevel() {
  return LEVEL_ORDER.reduce((map, level) => {
    // 排除清單要在去重「之前」套用。
    // 為什麼：若被排除的詞剛好是重複組的第一筆，先排除
    // 才能讓後面同音同字的另一個詞正常留下來（Python 端同此順序）。
    const reviewIds = loadReviewIdsForLevel(level);
    const rows = wordFileNamesForLevel(level).flatMap((fileName) => {
      const filePath = path.join(SOURCE_WORD_DIR, fileName);
      return readCsvRows(filePath).map((row) => normalizeSourceWord(row, level, fileName));
    }).filter((word) => !reviewIds.has(word.id));
    map[level] = uniqueFirstWordByReadingAndWriting(rows);
    return map;
  }, {});
}

function writeLevelFile(level, words) {
  const fileName = `word-level-${level.toLowerCase()}.js`;
  const outputWords = words.map(({ __sourceFile, __lineNumber, ...word }) => word);
  const output = [
    "// Generated by tools/dictionary/build_word_level_data.js. Do not edit by hand.",
    "window.FAT_SHIBA_WORD_LEVELS = window.FAT_SHIBA_WORD_LEVELS || {};",
    `window.FAT_SHIBA_WORD_LEVELS.${level} = ${JSON.stringify(outputWords)};`,
    ""
  ].join("\n");
  fs.writeFileSync(path.join(OUT_DIR, fileName), output);
}

function main() {
  const wordsByLevel = loadWordsByLevel();

  for (const level of LEVEL_ORDER) {
    writeLevelFile(level, wordsByLevel[level]);
  }

  const counts = LEVEL_ORDER.map((level) => `${level}:${wordsByLevel[level].length}`).join(" ");
  console.log(`Generated word level data: ${counts}`);
}

main();
