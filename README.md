# 呷胖環遊日本

手機直式優先、離線可玩的 JLPT 單字拼字遊戲。

## 專案結構

```text
fat_shiba/
├── web/              # 可部署網站根目錄
│   ├── index.html
│   ├── assets/
│   └── data/
├── tools/            # 本機開發與資料處理工具，不是網站 runtime
│   ├── ocr/
│   ├── audio/
│   └── prompts/
├── AGENT.md
└── DEV_TECH_SUMMARY.md
```

部署或開本機靜態服務時，請指定 `web/` 當網站根目錄。`tools/ocr/` 內的 PDF、Tesseract 語言資料與 OCR 輸出不需要也不應該在網站上提供。

## GitHub Pages 部署

這個 repo 已包含 GitHub Actions workflow：`.github/workflows/deploy-pages.yml`。推到 `main` 後，workflow 會把 `web/` 上傳成 GitHub Pages 網站根目錄。

第一次設定 GitHub Pages 時，請到 repo 的 `Settings` → `Pages`，將 `Source` 設為 `GitHub Actions`。如果仍使用 `Deploy from a branch` 且目錄選的是 repo root，GitHub Pages 會找不到真正的 `web/index.html`，根網址就可能出現 404。

根目錄的 `index.html` 只是 fallback redirect，正式部署應以 `web/` 作為網站根目錄。

## 本機開啟

這是靜態網站，可以直接打開：

```text
web/index.html
```

如果要用本機 server 測試相對路徑：

```bash
python3 -m http.server 8000 --directory web
```

測完記得停止 server，避免 port 被占住。

## 本機工具

OCR 抽詞：

```bash
python3 tools/ocr/extract_jlpt_vocab_from_pdf.py --pages 71-141 --level N4
python3 tools/ocr/extract_jlpt_vocab_from_pdf.py --pages 143-399 --level N3 --output tools/ocr/dictionary/jlpt_n3_wordlist_candidates.csv --raw-dir tools/ocr/outputs/n3_ocr_raw
python3 tools/ocr/prepare_jlpt_wordlist_from_candidates.py
```

合併清理後的 N4 詞庫到網站資料：

```bash
python3 tools/ocr/merge_n4_csv_wordlist.py
```

合併清理後的 N3 詞庫到網站資料：

```bash
python3 tools/ocr/merge_n3_csv_wordlist.py
python3 tools/ocr/fill_n3_zh_from_ocr_context.py
```

重新產生 N5 沖繩專心背景音樂 WAV：

```bash
python3 tools/audio/generate_n5_bgm.py
```

重新產生 N4 九州四國複習專注背景音樂 WAV：

```bash
python3 tools/audio/generate_n4_bgm.py
```

重新產生 N4 九州四國遊戲背景音樂 WAV：

```bash
python3 tools/audio/generate_n4_game_bgm.py
```
