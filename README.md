# html2slides

> 將 HTML 簡報轉為可逐項編輯的 PowerPoint，並提供 Google Slides 匯入與結構檢查。

有時候簡報已經用 HTML 排好，但交付時仍需要能編輯文字、形狀和圖片的 PowerPoint，而不是一張張截圖。`html2slides` 使用 Chromium 讀取排版資訊，產出中介模型（`DeckModel`），再轉成 PowerPoint 原生物件。也提供匯入 Google Slides 的選用流程。

這是針對既有測試範例持續改進的轉檔工具；**並非所有 HTML/CSS 效果都能無損轉換**。字型、瀏覽器與 Office／Google Slides 的排版差異仍需逐份檢查。

---

## 核心特色

- **純可編輯模式 (No-Screenshot Editable Mode)**：
  - 文字轉為 PowerPoint 原生 TextBox / TextFrame，支援獨立段落對齊 (Left, Center, Right, Justify)、字級、字重 (Bold) 與色彩。
  - 卡片與容器轉為原生 PowerPoint Shape (Rectangle, Rounded Rectangle, Solid Fill, Border, Left Accent Bar)。
  - 圖片轉為獨立可移動/縮放的 Picture Shape。
- **真實瀏覽器排版計算**：
  - 透過 Playwright Chromium 讀取 Flexbox、CSS Grid、Absolute 定位、Padding 與 Margin 等排版資訊。既有案例曾記錄小於 0.03 英吋的座標誤差；**這不是對所有 HTML 的普遍精度保證**。
- **字型與 CJK 相容性**：
  - 支援 `preserve` (保留 CSS 字型)、`override` (全域強制指定) 與 `map` (字型對應表) 三種模式。
  - 針對繁體中文／CJK 字元，集中以 OpenXML 標籤（`a:ea`、`a:latin`、`a:cs`）設定字型資訊，改善不同 Office 環境的字型識別；結果仍受接收端字型與匯入器影響。
- **Selector Overrides**：
  - 支援在 `html2slides.toml` 中為特定 CSS selector 注入覆寫樣式。
- **Google Slides 整合與回讀驗證**：
  - 透過最小權限 Google Drive API (`drive.file`) 自動將 PPTX 匯入並轉為原生 Google Slides。
  - 透過 Google Slides API 回讀頁面元素結構，檢查轉換結果；結構檢查不等於視覺排版完全一致。
- **嚴格安全性**：
  - 預設清除 `<script>` 與 inline `on*` 事件。
  - 預設禁止外部未授權網路連線 (`--allow-network` opt-in)。
- **結構化驗證報告**：
  - 自動產出 `conversion_report.json`，統計投影片數、Shape 數、Text 物件數、字型與對齊分佈。

---

## 安裝方式

```bash
# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝核心依賴
pip install -e .

# 安裝 Playwright Chromium 瀏覽器
playwright install chromium

# (選配) 安裝 Google Slides 整合依賴
pip install -e ".[google]"
```

---

## 使用方式

### 1. 最基本轉檔 (產生可編輯 PPTX)
```bash
html2slides presentation.html
```
輸出：
```text
output/
└── presentation.pptx
```

### 2. 指定輸出路徑與 Slide Selector
```bash
html2slides presentation.html -o output/my_deck.pptx --slide-selector ".slide-container"
```

### 3. 強制指定字型 (Override Mode)
```bash
html2slides presentation.html --font "Noto Sans TC" --font-mode override
```

### 4. 轉檔並直接同步至 Google Slides
```bash
html2slides presentation.html --google-slides
```
輸出：
```text
output/
├── presentation.pptx
├── presentation_google_slides_url.txt
└── conversion_report.json
```

---

## 命令列參數 (CLI Options)

| 參數 | 說明 |
| :--- | :--- |
| `input` | 輸入 HTML 簡報檔案路徑 |
| `-o, --output` | 輸出 PPTX 檔案路徑 (預設: `output/<input_stem>.pptx`) |
| `--config` | 指定 TOML 設定檔 (如 `html2slides.toml`) |
| `--slide-selector` | 投影片容器之 CSS selector (預設: `.slide-container` 或 `.slide`) |
| `--font` | 預設或覆寫字型名稱 (例如 `"Noto Sans TC"`) |
| `--font-mode` | 字型解析模式 (`preserve` / `override` / `map`) |
| `--google-slides` | 上傳至 Google Drive 並自動轉為原生 Google Slides |
| `--drive-folder-id`| Google Drive 目標資料夾 ID |
| `--strict` | 嚴格模式 (遇任何 warning 視為失敗) |
| `--allow-network` | 允許載入遠端網路資源 (預設關閉) |
| `--allow-javascript`| 允許執行 HTML 中的 JavaScript (預設關閉) |
| `--report` | 產出 `conversion_report.json` (預設開啟) |

---

## 設定檔範例 (`html2slides.toml`)

```toml
[deck]
slide_selector = ".slide-container"
width_in = 13.333
height_in = 7.5

[fonts]
mode = "preserve"
default = "Noto Sans TC"

[fonts.map]
"Segoe UI" = "Noto Sans TC"
"Arial" = "Aptos"
"Inter" = "Noto Sans TC"

[[overrides]]
selector = ".kicker"
font_size_pt = 14.0
font_weight = 800

[[overrides]]
selector = ".takeaway-bar"
font_size_pt = 16.0
font_weight = 700

[security]
allow_network = false
allow_javascript = false
```

---

## 測試與驗證

專案保留自動化測試與[歷史實作報告](IMPLEMENTATION_RESULT.md)；報告中的 10/10 PASS 與座標誤差數據屬當時環境及測試範例，不是本次重新執行。Google Slides 的 API 結構測試也不等於所有實際帳戶、字型及佈景都完成端到端驗收。

```bash
# 執行完整測試套件
pytest -v

# 執行 Corning 6 頁黃金回歸測試
pytest tests/test_corning_regression.py -v
```

---

## 授權條款

MIT License
