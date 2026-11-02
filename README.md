# html2slides｜讓 HTML 簡報變成可編輯的 PowerPoint

用 HTML 和 CSS 製作簡報很方便，但交付給同事時，如果只把畫面截成圖片貼到 PowerPoint，文字、卡片、圖形就不能再個別修改。

`html2slides` 把網頁簡報轉成 **PowerPoint 原生文字方塊、圖形與圖片**。它使用 Chromium 讀取 CSS 排版結果，再經過中介模型（`DeckModel`）輸出 PPTX；需要時也能將 PPTX 匯入 Google Slides。

## 主要功能

- **物件可編輯**：文字、卡片、邊框和圖片分別輸出，方便調整內容與位置，而不只是整頁截圖。
- **解析網頁排版**：透過 Playwright 取得 Flexbox、Grid、定位和間距資訊，減少手動重排。
- **處理繁體中文字型**：支援保留原字型、統一覆寫與字型對應表，並寫入 PowerPoint 的 CJK 字型資訊。
- **彈性控制轉換**：可指定投影片的 CSS selector、輸出路徑、字型與 TOML 設定。
- **選用 Google Slides 匯入**：使用 Drive API 匯入，再透過 Slides API 回讀物件結構。
- **產出檢查報告**：轉換後提供投影片、文字與 Shape 等統計資訊。

## 快速開始

需要 Python 3.11 以上，以及 Playwright Chromium。建立虛擬環境並啟用後，執行：

```bash
pip install -e .
playwright install chromium
html2slides presentation.html
```

預設產生 `output/presentation.pptx`。

指定投影片容器與輸出位置：

```bash
html2slides presentation.html -o output/my_deck.pptx --slide-selector ".slide-container"
```

使用統一字型：

```bash
html2slides presentation.html --font "Noto Sans TC" --font-mode override
```

如需 Google Slides，先準備可用的 Google API 授權，再安裝選用套件並執行：

```bash
pip install -e ".[google]"
html2slides presentation.html --google-slides
```

## 轉換架構

```text
HTML + CSS
    ↓
Chromium 計算排版
    ↓
擷取文字、形狀、圖片、位置與樣式
    ↓
DeckModel
    ↓
PPTX 原生物件
    └─ 選用：Google Slides 匯入與結構檢查
```

我把瀏覽器擷取、PPTX 渲染與驗證拆成模組，讓字型、選擇器和物件轉換規則可以獨立調整。

## 測試與結果

專案有一套 **6 頁 HTML 簡報的回歸測試**，檢查投影片數量、尺寸、文字內容及物件結構。測試條件可直接查看 [test_corning_regression.py](tests/test_corning_regression.py)。

```bash
pip install -e ".[dev]"
pytest -v
pytest tests/test_corning_regression.py -v
```

既有案例曾記錄小於 0.03 英吋的座標誤差，但不是對所有 HTML/CSS 的精度保證。Google Slides 的元素結構回讀，也不等於在所有字型或裝置上的視覺排版完全一致。

複雜動畫、特殊 CSS 與網頁互動不一定能完整轉成 PowerPoint 物件。對外交付前，建議使用實際簡報檢查字型與排版。

## 原始碼與授權

- [CLI 入口](src/html2slides/cli.py)
- [專案套件設定](pyproject.toml)
- 授權：MIT
