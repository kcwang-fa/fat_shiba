# 呷胖環遊日本 Phase 1｜開發技術摘要

## Phase 2 更新備註

目前網站入口為 `web/index.html`，已擴充成 Phase 2 單檔版本：

- 日本五區資料已建立：N5 沖繩 10 站、N4 九州四國 15 站、N3 中國關西 20 站、N2 關東中部 30 站、N1 東北北海道 35 站。目前入口只開放 N5，N4-N1 先標示製作中，等明信片素材完成再重新開放。
- 棋盤依等級切換：N5 是 4×4，N4/N3 是 5×5，N2/N1 是 6×6。
- 過站門檻依等級切換：N5/N4 每站 10 詞，N3 每站 12 詞，N2/N1 每站 15 詞。
- 詞庫邏輯已改成累加制：例如 N3 場可命中 N5/N4/N3 詞；但只有當前等級詞會計入過站。
- 保底詞只會從當前等級挑選。
- 各區進度分開存在 `localStorage`，root save 只保存目前區域與遊戲模式。
- 右上角換盤鈕會整盤重抽，清掉本局選取、提示與本盤已找到狀態，但不清區域進度。

詞庫資料目前先內嵌每級核心常用詞子集，玩法與資料結構已支援大型詞庫；若要達到 N4 約 1500、N3 約 3700、N2 約 6000、N1 約 10000+，後續應把正式授權或自建整理過的詞庫用同樣欄位格式補入 `RAW_WORDS_BY_LEVEL`，不要用假資料灌數量。

## 2026-07-17 目前進度

本輪進度已把 Phase 2 從「五區骨架」推進到「大詞庫匯入、複習 metadata、分場景 BGM」的狀態。重點如下：

- `web/data/word_data.js` 已新增 Eggrolls JLPT10k v3.5 匯入區塊：`EGGROLLS_N5_WORD_ROWS_TEXT`、`EGGROLLS_N4_WORD_ROWS_TEXT`、`EGGROLLS_N3_WORD_ROWS_TEXT`、`EGGROLLS_N2_WORD_ROWS_TEXT`、`EGGROLLS_N1_WORD_ROWS_TEXT`。
- 前端 `web/index.html` 會用 `buildImportedWordRows()` 把 Eggrolls 區塊併入 `RAW_WORDS_BY_LEVEL`，並用「正規化讀音 + writing」去重，避免新匯入詞把既有手工詞 ID 洗牌。
- 目前詞庫區塊筆數：
  - N5：核心 750 + Eggrolls 163 = 913。
  - N4：base 60 + extra 679 + CSV 235 + Eggrolls 152 = 1,126。
  - N3：base 60 + extra 2,285 + Eggrolls 730 = 3,075。
  - N2：base 56 + extra 1,337 + Eggrolls 2,005 = 3,398。
  - N1：base 50 + OCR extra 2,106 + Eggrolls 3,585 = 5,741。
- N1 OCR 匯入流程已新增 `tools/ocr/merge_n1_csv_wordlist.py`，輸出保守清理後的 `tools/ocr/dictionary/jlpt_n1_wordlist_cleaned_for_game.csv`、拒收清單與 import audit。N1 來源仍應視為 OCR 派生資料，後續正式發布前要抽樣校對讀音、表記與中文義。
- Eggrolls Anki 匯入流程已新增 `tools/anki/import_eggrolls_missing_words.py`，用獨立 `EGGROLLS_N*_WORD_ROWS_TEXT` 區塊保存新增詞，避免改動既有手工詞列。
- `tools/dictionary/build_word_meta.py` 已擴充到 N4/N1 例句資料、Eggrolls note metadata、更多詞性分類與動詞類型推斷。`tools/dictionary/n4_examples.csv` 目前 820 筆資料列，`tools/dictionary/n1_examples.csv` 目前 2,125 筆資料列。
- `web/data/word_meta.js` 已重新產生，目前約 9,837 筆 metadata，可供單字卡/複習模式讀取詞性、例句、備註等輔助資訊。
- `README.md` 已補上 N4/N1 例句維護方式，以及 N5 game BGM、N1 review BGM 的重新產生指令。
- `web/index.html` 已把 N5 複習 BGM 與 N5 遊戲 BGM 分開；N4 遊戲/複習 BGM 維持獨立；N1 已新增遊戲 BGM 與複習壁爐 BGM。切換遊戲/複習/區域時會停止其他場景音訊，避免多條音軌疊在一起。
- N1 東北北海道 35 站已補 `travelLog` 文案，過站明信片 modal 可顯示完整旅遊日記，不再只靠 fallback 句。
- `web/service-worker.js` 快取版本已升到 `fat-shiba-pwa-v5`，並更新 `word_data.js` / `word_meta.js` 查詢字串，避免舊快取卡住新詞庫。快取這東西很乖的時候像工具，不乖的時候像考驗修養。
- 音訊資產已更新或新增：
  - N5：`n5-okinawa-focus-bgm.*`、`n5-okinawa-game-bgm.*`。
  - N4：`n4-kyushu-shikoku-bgm.*`、`n4-kyushu-shikoku-game-bgm.*`。
  - N1：`n1-tohoku-hokkaido-bgm.*`、`n1-tohoku-hokkaido-review-bgm.*`。
  - 另有 `fireplace-white-noise-bgm.*` 作為壁爐/白噪音素材方向。
- `tools/audio/` 目前有多個 deterministic 產生器，包含 N5/N4/N1 遊戲與複習方向、溪流、壁爐白噪音等；`audio_analysis/` 與 `generated_audio/` 內留有波形、頻譜與測試輸出，供音訊調整對照。

### 待驗證與風險

- 大詞庫已併入資料結構，但尚未逐級完整人工校對；N1 OCR 與 Eggrolls 來源都需要抽樣檢查，尤其是長音、表記、同音異義與中文義。
- `word_meta.js` 已大幅膨脹，後續若載入效能受影響，應考慮依等級分檔或 lazy load；現在先維持單檔，方便離線 PWA 與單檔前端邏輯。
- 新音訊資產已接到前端，但仍要做實機聽感測試，確認音量、loop 接點、iOS autoplay 行為與 PWA 離線快取都正常。
- service worker 版本已更新，但若使用者瀏覽器卡舊快取，測試時要重新整理或清站台資料確認。

## 等級休息場景與聲音方向

| 等級 | 休息場景 | 畫面感 | 音樂 / 環境音 |
|---|---|---|---|
| N5 | 沖繩狗屋前的午後 | 呷胖趴在紅瓦狗屋旁，旁邊有扶桑花、小水碗、遠方海面很亮 | 海風、遠處浪聲、很淡的三線撥弦 |
| N4 | 九州四國溫泉旅館 | 呷胖泡完腳湯，坐在榻榻米上擦毛，旁邊有梅枝餅或烏龍麵 | 木造旅館室內感、溫泉水聲、低音量木琴 / 箏 |
| N3 | 關西町家雨天窗邊 | 呷胖坐在京都町家窗邊，看雨滴落在石板路，旁邊放著抹茶和筆記本 | 細雨聲、室內安靜空氣、非常稀疏的鋼琴 |
| N2 | 關東中部湖畔夜營 | 呷胖在富士山附近湖畔帳篷前，披小毯子看單字卡，營燈暖暖的 | 夜風、湖水、營火很小聲、低頻 pad |
| N1 | 東北北海道雪屋暖爐旁 | 呷胖窩在雪國木屋裡，外面下雪，牠靠著暖爐睡到快點頭 | 雪風、暖爐柴火、很慢的柔和鋼琴 / 空氣音 |

## 專案定位

「呷胖環遊日本」是一款包著美食旅行遊戲皮的 JLPT 單字卡。玩家操作圓滾滾水彩貪吃柴「呷胖」，透過 4×4 假名棋盤拼出 N5 單字，賺飯錢、通過沖繩站點、收集明信片。

Phase 1 只做一個完整可玩迴圈：

```text
進入沖繩站點
→ 產生 4×4 平假名棋盤
→ 玩家點選棋盤假名拼字
→ 命中 N5 單字
→ 顯示單字卡 5 秒
→ 累積站點進度
→ 拼滿 10 個 N5 單字
→ 過站演出
→ 取得明信片
→ 進下一站
```

## 技術原則

- 網站 runtime 放在 `web/`，入口是 `web/index.html`。
- 手機直式優先。
- 離線可玩。
- 不需要後端、不需要帳號、不需要網路。
- 不載入 Google Fonts、CDN 或其他外部執行期資源；離線冷啟動不能等待外部請求。
- 圖片放在 `web/assets/`。
- 明信片圖片缺檔時必須有 CSS fallback，不可以畫面破掉。
- OCR、詞庫清理、音樂產生與圖片提示詞等本機工具放在 `tools/`，不要放進網站根目錄。
- Phase 1 以「核心手感穩」優先，功能不要擴張到 N4、混合假名棋盤、音效或排行榜。

## 檔案結構

目前專案把可部署網站與本機工具分開：

```text
fat_shiba/
├── web/
│   ├── index.html
│   ├── assets/
│   └── data/
│       └── word_data.js
├── tools/
│   ├── ocr/
│   │   ├── extract_jlpt_vocab_from_pdf.py
│   │   ├── merge_n4_csv_wordlist.py
│   │   ├── dictionary/
│   │   └── tessdata/
│   ├── audio/
│   │   └── generate_n4_bgm.py
│   └── prompts/
├── DEV_TECH_SUMMARY.md
└── AGENT.md
```

部署或本機靜態服務應指定 `web/` 為網站根目錄。`tools/ocr/` 內的 PDF、Tesseract 語言資料與 OCR 中間產物不屬於前端 runtime。

## 沖繩站點資料

```js
const OKINAWA_STATIONS = [
  {
    id: "okinawa_01",
    placeZh: "出發的狗屋",
    placeJa: "出発の犬小屋",
    foodZh: "沖繩麵",
    foodJa: "沖縄そば",
    scenePrompt: "沖繩鄉間的一間小狗屋作為旅程起點，紅瓦屋頂、白色石牆、扶桑花與熱帶植物，遠方可見藍色海洋，一隻旅行小狗背著行李準備出發",
    postcard: "assets/postcard_okinawa_01.jpg"
  },
  {
    id: "okinawa_02",
    placeZh: "那霸國際通",
    placeJa: "国際通り",
    foodZh: "沙翁甜甜圈",
    foodJa: "サーターアンダギー",
    scenePrompt: "沖縄県那覇市の国際通り，從街道中央觀看，兩側是沖繩土產店、餐廳、紅瓦裝飾、招牌與棕櫚樹，街上有少量行人",
    postcard: "assets/postcard_okinawa_02.jpg"
  },
  {
    id: "okinawa_03",
    placeZh: "首里城",
    placeJa: "首里城",
    foodZh: "金楚糕",
    foodJa: "ちんすこう",
    scenePrompt: "沖縄県那覇市の首里城，正面觀看鮮紅色琉球式宮殿、中央石階、紅色木造建築與左右對稱的城郭",
    postcard: "assets/postcard_okinawa_03.jpg"
  },
  {
    id: "okinawa_04",
    placeZh: "波上宮海灘",
    placeJa: "波上宮・波の上ビーチ",
    foodZh: "海葡萄小碗",
    foodJa: "海ぶどう",
    scenePrompt: "沖縄県那覇市の波の上ビーチ，碧藍海水、白色沙灘與岩石海岸，岩崖上方可見朱紅色波上宮",
    postcard: "assets/postcard_okinawa_04.jpg"
  },
  {
    id: "okinawa_05",
    placeZh: "美麗海水族館",
    placeJa: "沖縄美ら海水族館",
    foodZh: "海鹽冰淇淋",
    foodJa: "海塩アイス",
    scenePrompt: "沖縄美ら海水族館の黒潮の海水槽，巨大鯨鯊游過深藍色水槽，周圍有鬼蝠魟與魚群",
    postcard: "assets/postcard_okinawa_05.jpg"
  },
  {
    id: "okinawa_06",
    placeZh: "萬座毛",
    placeJa: "万座毛",
    foodZh: "苦瓜炒蛋",
    foodJa: "ゴーヤーチャンプルー",
    scenePrompt: "沖縄県恩納村の万座毛，象鼻形琉球石灰岩海崖、綠色草地、藍綠色海水與白色浪花",
    postcard: "assets/postcard_okinawa_06.jpg"
  },
  {
    id: "okinawa_07",
    placeZh: "古宇利大橋",
    placeJa: "古宇利大橋",
    foodZh: "紅芋塔",
    foodJa: "紅芋タルト",
    scenePrompt: "沖縄県今帰仁村の古宇利大橋，從高處俯瞰筆直長橋跨越藍綠色海水，遠方是古宇利島",
    postcard: "assets/postcard_okinawa_07.jpg"
  },
  {
    id: "okinawa_08",
    placeZh: "竹富島",
    placeJa: "竹富島",
    foodZh: "八重山黑糖冰",
    foodJa: "八重山黒糖かき氷",
    scenePrompt: "沖縄県竹富島の伝統集落，白砂道路、紅瓦屋頂、石牆、扶桑花與緩慢行走的水牛車",
    postcard: "assets/postcard_okinawa_08.jpg"
  },
  {
    id: "okinawa_09",
    placeZh: "石垣島",
    placeJa: "石垣島・川平湾",
    foodZh: "石垣牛漢堡",
    foodJa: "石垣牛バーガー",
    scenePrompt: "沖縄県石垣島の川平湾，從高處眺望翠綠島嶼、白色沙灘與清澈的藍綠色海灣",
    postcard: "assets/postcard_okinawa_09.jpg"
  },
  {
    id: "okinawa_10",
    placeZh: "玉泉洞",
    placeJa: "おきなわワールド・玉泉洞",
    foodZh: "扁實檸檬果汁",
    foodJa: "シークヮーサージュース",
    scenePrompt: "沖縄県南城市のおきなわワールド玉泉洞，巨大鐘乳石、石筍、地下水面與洞穴步道，神秘但明亮安全",
    postcard: "assets/postcard_okinawa_10.jpg"
  }
];
```

注意：站點食物名稱可以含片假名與長音 `ー`。可拼詞庫會把長音符正規化成前一個假名對應的母音，`ー` 本身不進棋盤。

## 假名與字典規則

### 棋盤

- 4×4。
- 每格一個平假名單位。
- 棋格支援滑鼠、觸控與鍵盤 Enter/Space 選字。
- 可包含濁音、半濁音、小字。
- 小字 `ゃ`、`ゅ`、`ょ`、`っ` 視為獨立棋格。
- `ー` 不進棋盤。
- 玩家可依序點選棋盤上的任意假名，不要求相鄰。
- 同一個單字不可重複使用同一格。

### 比對

內部比對一律使用 `normalizedReading`。

- 平假名讀音保持平假名。
- 片假名讀音轉為平假名。
- 長音符 `ー` 轉為前一個假名對應的母音，例如 `コーヒー` 正規化為 `こおひい`。

範例：

```text
ばす → バス
てれび → テレビ
ぱん → パン
こおひい → コーヒー
がっこう → 学校
```

### 字典資料格式

```js
{
  id: "n5_0001",
  reading: "バス",
  normalizedReading: "ばす",
  writing: "バス",
  zh: "公車",
  level: "N5",
  script: "katakana"
}
```

漢字詞：

```js
{
  id: "n5_0002",
  reading: "がっこう",
  normalizedReading: "がっこう",
  writing: "学校",
  zh: "學校",
  level: "N5",
  script: "kanji"
}
```

同音詞全收，不要合併。已拼過清單應記錄單字 `id`，不要只記 `normalizedReading`，避免 `はし` 這類同音詞互相污染。

## 棋盤生成

每局根據 N5 詞庫的 `normalizedReading` 統計假名頻率，建立抽字權重。

要求：

- 常見假名較容易出現。
- 小字、濁音、半濁音要有限制，避免棋盤過難。
- 每局埋入 3 到 5 個可依序任意選格的 N5 目標詞。
- 優先埋入玩家尚未拼過的詞。
- 若未見詞不足，再從已拼過詞補足。
- 棋盤生成後要能知道本盤還藏幾個尚未找到的保底詞。

## 命中與單字卡

玩家選取路徑後，組成假名字串。字串完全等於某筆字典資料的 `normalizedReading` 時命中。

命中後顯示單字卡 5 秒。

漢字詞格式：

```text
がっこう／学校
學校
[N5]
```

片假名詞格式：

```text
ばす／バス
公車
[N5]
```

讀音與寫法相同時可簡化：

```text
ちょっと
稍微、一點
[N5]
```

同一局同一個單字只算一次。跨局是否再次顯示卡片可以保留，但已拼過清單仍應避免重複計入「未見詞」。

## 提示與防卡關

- 每局 3 次提示。
- 點提示後，亮起一個尚未找到的保底詞首字。
- 亮起時間 2 秒。
- 不顯示完整答案、不顯示完整路徑。
- 顯示本盤保底剩餘數，例如：

```text
本盤還藏 4 個目標詞
```

## 過站與明信片

- 沖繩共 10 站。
- 每站拼滿 10 個 N5 單字即可過站。
- 同站可無限重進，不鎖死。
- 過站後顯示簡易慶祝文字、日記佔位文、明信片入手。
- 第 10 站完成後顯示沖繩區完成訊息。

明信片優先讀取站點的 `postcard` 圖片。圖片缺檔或載入失敗時，顯示 CSS fallback 卡。

fallback 內容建議：

```text
首里城
ちんすこう
金楚糕
```

## 存檔

使用 `localStorage`。建議 key：

```js
const SAVE_KEY = "fatShiba.phase1.save.v1";
```

資料格式：

```js
{
  currentStationId: "okinawa_03",
  completedStationIds: ["okinawa_01", "okinawa_02"],
  collectedPostcardIds: ["okinawa_01", "okinawa_02"],
  foundWordIds: ["n5_0001", "n5_0002"],
  stationWordCounts: {
    okinawa_03: 7
  }
}
```

要求：

- 重新整理後進度仍在。
- 存檔壞掉時回到初始狀態，不可以白畫面。
- 提供重置進度按鈕。
- 重置進度需要二次確認。

## UI 配置

手機直式優先。建議結構：

```text
頂部：目前站點、食物、過站進度
中段：4×4 假名棋盤
下段：目前拼字、送出、清除、提示
底部：地圖進度、明信片入口
```

設計要求：

- 按鈕與棋格要適合手指點擊。
- 棋格尺寸固定，不因 hover、選取、提示、字體載入造成跳動。
- 不要把說明文字塞滿畫面。
- 主要畫面第一眼就要能開始玩。
- 視覺風格溫暖、水彩、留白多，但 UI 仍要清楚。

## Phase 1 不做項目

- 混合平假名／片假名棋盤。
- 長音 `ー` 的拼字規則。
- N4 以上詞庫。
- 日本全國地圖。
- 自動圖片生成流程。
- 音效與語音。
- 排行榜。
- 帳號登入。
- 多人或雲端同步。

## 驗收清單

```text
□ web/index.html 可啟動
□ 手機直式可玩
□ 離線可玩
□ 冷啟動離線時不請求 Google Fonts 或其他外部資源
□ 棋格可用 Enter/Space 鍵盤選字
□ 4×4 棋盤可點選假名拼字
□ 小字 ゃゅょっ 可作為獨立棋格
□ ー 不進棋盤
□ 長音詞會正規化為母音，例如 コーヒー → こおひい
□ 拼得出 がっこう，並命中 学校
□ 拼得出 ちょっと
□ 拼 ばす 可命中 バス
□ 片假名詞會轉成平假名讀音比對
□ 每局有 3 到 5 個保底詞
□ 未見詞優先進保底
□ 提示鈕每局 3 次
□ 提示亮首字 2 秒
□ 顯示「本盤還藏 N 個目標詞」
□ 每站拼滿 10 個 N5 單字可過站
□ 沖繩 10 站可完整通關
□ 過站後取得對應明信片
□ 明信片圖片缺檔時 fallback 正常
□ localStorage 保存進度、已拼單字、已得明信片
□ 重新整理後進度仍在
□ 重置進度有二次確認
```

## 開發順序建議

1. 建立 `web/index.html` 骨架與手機直式 CSS。
2. 放入沖繩 10 站資料。
3. 建立 N5 字典資料格式與 kana normalizer。
4. 實作 4×4 棋盤與任意位置選字。
5. 實作字典命中與單字卡。
6. 實作骰面頻率與棋盤生成。
7. 實作保底埋詞與未見詞優先。
8. 實作提示鈕與目標詞計數器。
9. 實作過站、明信片與 fallback 卡。
10. 實作 `localStorage` 存檔、讀檔與重置。
11. 做手機直式 smoke test 與驗收測試。
