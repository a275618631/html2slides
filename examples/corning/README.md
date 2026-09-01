# Corning 76964 Interview Deck — Regression Fixture

本範例為 Corning 76964 Applied AI Solution Architect 6 頁簡報的黃金測試樣本 (Golden Fixture)。

## 包含檔案
- `deck_20260901.html`: 原始 6 頁 HTML 投影片源碼 (16:9, `.slide-container`)
- `build_corning_deck_20260901.py`: 舊版手工 python-pptx 生成腳本 (保留作為 Regression 比對參考)
- `README_20260901.md`: 原始面試規格與 Guardrails 說明文件

## 轉換命令
使用通用 `html2slides` 工具執行轉換：

```bash
html2slides examples/corning/deck_20260901.html -o output/corning_deck.pptx
```
