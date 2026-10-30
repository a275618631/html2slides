# html2slides｜把 HTML 簡報轉成可編輯的 PowerPoint

用 HTML 和 CSS 製作簡報很方便，卻常遇到一個問題：交付時如果只把畫面截圖貼進 PowerPoint，收件人就無法調整文字、圖形和排版。

我開發 `html2slides`，讓網頁版簡報可以轉成 **PowerPoint 原生、可分別編輯的物件**，並可選擇轉成 Google Slides。它透過 Chromium 讀取實際排版位置，建立中介模型，再輸出文字方塊、形狀和圖片，而不是把整頁當成一張圖片。

## 能做什麼

- **保留文字編輯能力**：文字轉成 PowerPoint 的 TextBox，保留常見字型、字級、粗細、顏色和對齊方式。
- **保留圖形結構**：卡片、色塊與邊框輸出成可移動、可調整的 Shape；圖片也能獨立移動。
- **解析網頁排版**：使用 Playwright Chromium 取得 Flexbox、Grid、定位與間距資訊，減少手動重排。
- **處理中英文字型**：提供保留原字型、統一指定字型及字型對應表三種方式，並處理 PowerPoint 的 CJK 字型設定。
- **選擇性匯入 Google Slides**：透過 Google Drive API 將產生的 PPTX 匯入，並檢查簡報元素結構。
- **輸出檢查報告**：轉換時產生 `conversion_report.json`，記錄投影片與各類物件的統計資訊。

## 快速試用

需要 Python 3.11 以上。先安裝套件與 Playwright 使用的 Chromium：

```bash
python -m venv .venv
# 啟用虛擬環境後
pip install -e .
playwright install chromium
```

將 HTML 簡報轉成 PowerPoint：

```bash
html2slides presentation.html
```

預設輸出為 `output/presentation.pptx`。想指定位置、投影片容器或字型，可用：

```bash
html2slides presentation.html -o output/my_deck.pptx --slide-selector ".slide-container"
html2slides presentation.html --font "Noto Sans TC" --font-mode override
```

如果已設定 Google 授權環境，還可以安裝選用相依套件後匯入 Google Slides：

```bash
pip install -e ".[google]"
html2slides presentation.html --google-slides
```

這個步驟需要有效的 Google API 授權與可存取的 Drive 目的地。

## 轉換流程

```text
HTML 簡報
   ↓
Chromium 計算 CSS 排版
   ↓
擷取文字、形狀、圖片與位置
   ↓
DeckModel 中介表示
   ↓
PowerPoint 原生物件
   ├─ .pptx
   └─ 選用：匯入 Google Slides
```

我把網頁解析與 PPTX 產生分成不同模組，讓字型處理、選擇器與轉換規則可以各自調整，也更容易寫回歸測試。

## 常用選項

| 參數 | 用途 |
| --- | --- |
| `-o, --output` | 自訂 PPTX 輸出路徑 |
| `--slide-selector` | 指定哪個 HTML 元素代表一張投影片 |
| `--font`、`--font-mode` | 指定字型與字型處理模式 |
| `--config` | 讀取 TOML 設定 |
| `--google-slides` | 啟用 Google Slides 匯入 |
| `--strict` | 將轉換警告視為失敗 |
| `--allow-network` | 允許載入外部網路資源（預設關閉） |
| `--allow-javascript` | 允許執行 HTML 的 JavaScript（預設關閉） |

詳細參數可使用 `html2slides --help` 查看。設定檔 `html2slides.toml` 可指定投影片尺寸、字型對應、特定 CSS selector 的樣式覆寫與安全選項。

## 測試與實作

專案包含六頁 HTML 簡報的回歸測試，檢查投影片數量、文字內容、尺寸以及輸出的 PowerPoint 物件。測試程式位於 [tests/test_corning_regression.py](tests/test_corning_regression.py)，可以直接查看驗收條件。

```bash
pip install -e ".[dev]"
pytest -v
pytest tests/test_corning_regression.py -v
```

執行測試時需要 Chromium 和相關 Python 套件；測試內容與預期結果可直接對照原始測試程式。

## 適用情境

適合需要把 HTML 設計稿交給其他人繼續修改的簡報製作流程。複雜動畫、特殊 CSS 和網頁專屬互動未必能原樣對應到 PowerPoint 物件；可先用測試範例確認實際需要保留的元素。

## 授權

MIT License。
