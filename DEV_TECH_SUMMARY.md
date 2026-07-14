# 呷胖環遊日本 Phase 1｜開發技術摘要

## Phase 2 更新備註

目前 `index.html` 已擴充成 Phase 2 單檔版本：

- 日本五區全開：N5 沖繩、N4 九州四國、N3 中國關西、N2 關東中部、N1 東北北海道，各 10 站。
- 棋盤依等級切換：N5 是 4×4，N4/N3 是 5×5，N2/N1 是 6×6。
- 過站門檻依等級切換：N5/N4 每站 10 詞，N3 每站 12 詞，N2/N1 每站 15 詞。
- 詞庫邏輯已改成累加制：例如 N3 場可命中 N5/N4/N3 詞；但只有當前等級詞會計入過站。
- 保底詞只會從當前等級挑選。
- 各區進度分開存在 `localStorage`，root save 只保存目前區域與遊戲模式。
- 右上角換盤鈕會整盤重抽，清掉本局選取、提示與本盤已找到狀態，但不清區域進度。

詞庫資料目前先內嵌每級核心常用詞子集，玩法與資料結構已支援大型詞庫；若要達到 N4 約 1500、N3 約 3700、N2 約 6000、N1 約 10000+，後續應把正式授權或自建整理過的詞庫用同樣欄位格式補入 `RAW_WORDS_BY_LEVEL`，不要用假資料灌數量。

## 專案定位

「呷胖環遊日本」是一款包著美食旅行遊戲皮的 JLPT 單字卡。玩家操作圓滾滾水彩貪吃柴「呷胖」，透過 4×4 假名棋盤拼出 N5 單字，賺飯錢、通過沖繩站點、收集明信片。

Phase 1 只做一個完整可玩迴圈：

```text
進入沖繩站點
→ 產生 4×4 平假名棋盤
→ 玩家點選棋盤假名拼字
→ 命中 N5 單字
→ 顯示單字卡 2 秒
→ 累積站點進度
→ 拼滿 10 個 N5 單字
→ 過站演出
→ 取得明信片
→ 進下一站
```

## 技術原則

- 起步使用單檔 `index.html`。
- 手機直式優先。
- 離線可玩。
- 不需要後端、不需要帳號、不需要網路。
- 圖片放在 `assets/`。
- 明信片圖片缺檔時必須有 CSS fallback，不可以畫面破掉。
- Phase 1 以「核心手感穩」優先，功能不要擴張到 N4、混合假名棋盤、音效或排行榜。

## 檔案結構建議

Phase 1 起步可以維持很小：

```text
fat_shiba/
├── index.html
├── DEV_TECH_SUMMARY.md
├── AGENT.md
└── assets/
    ├── postcard_okinawa_01.jpg
    ├── postcard_okinawa_02.jpg
    ├── postcard_okinawa_03.jpg
    ├── postcard_okinawa_04.jpg
    ├── postcard_okinawa_05.jpg
    ├── postcard_okinawa_06.jpg
    ├── postcard_okinawa_07.jpg
    ├── postcard_okinawa_08.jpg
    ├── postcard_okinawa_09.jpg
    └── postcard_okinawa_10.jpg
```

`assets/` 與明信片圖片可以晚點補，但程式一開始就要支援 fallback。

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

注意：站點食物名稱可以含片假名與長音 `ー`，但 Phase 1 拼字詞庫仍排除含 `ー` 的可拼單字。這兩件事是不同層級，不要混在一起。

## 假名與字典規則

### 棋盤

- 4×4。
- 每格一個平假名單位。
- 可包含濁音、半濁音、小字。
- 小字 `ゃ`、`ゅ`、`ょ`、`っ` 視為獨立棋格。
- `ー` 不進棋盤。
- 玩家可依序點選棋盤上的任意假名，不要求相鄰。
- 同一個單字不可重複使用同一格。

### 比對

內部比對一律使用 `normalizedReading`。

- 平假名讀音保持平假名。
- 片假名讀音轉為平假名。
- 含 `ー` 的詞在 Phase 1 從可拼詞庫排除。

範例：

```text
ばす → バス
てれび → テレビ
ぱん → パン
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
- 每局埋入 3 到 5 個可連路徑的 N5 目標詞。
- 優先埋入玩家尚未拼過的詞。
- 若未見詞不足，再從已拼過詞補足。
- 棋盤生成後要能知道本盤還藏幾個尚未找到的保底詞。

## 命中與單字卡

玩家選取路徑後，組成假名字串。字串完全等於某筆字典資料的 `normalizedReading` 時命中。

命中後顯示單字卡 2 秒。

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
□ 單檔 index.html 可啟動
□ 手機直式可玩
□ 離線可玩
□ 4×4 棋盤可點選假名拼字
□ 小字 ゃゅょっ 可作為獨立棋格
□ ー 不進棋盤
□ 拼得出 がっこう，並命中 学校
□ 拼得出 ちょっと
□ 拼 ばす 可命中 バス
□ 片假名詞會轉成平假名讀音比對
□ 含 ー 的詞不進 Phase 1 可拼詞庫
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

1. 建立 `index.html` 骨架與手機直式 CSS。
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
