# 企業智慧製造 AI 解決方案架構簡報範例 (Enterprise AI Deck Fixture)

本範例為 6 頁企業級 AI 解決方案架構簡報的驗證樣本 (Regression Fixture)。

## 包含檔案
- `deck_sample.html`: 6 頁標準 HTML 投影片源碼 (16:9, `.slide-container` 佈局)
- `build_enterprise_deck.py`: 參考生成腳本 (保留作為 Regression 比對參考)

## 轉換命令
使用 `html2slides` 工具執行轉換：

```bash
html2slides examples/enterprise_ai_deck/deck_sample.html -o output/enterprise_deck.pptx
```
