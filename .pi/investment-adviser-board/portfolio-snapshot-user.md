# Portfolio Snapshot Pointer

最新人工確認的使用者投資組合快照：

- JSON：`.pi/investment-adviser-board/portfolio-records/2026-04-03/portfolio-snapshot-user-2026-04-03.json`
- Markdown：`.pi/investment-adviser-board/portfolio-records/2026-04-03/portfolio-snapshot-user-2026-04-03.md`
- JSON Pointer：`.pi/investment-adviser-board/portfolio-snapshot-user.json`

## 規則
- 新的人工快照應存放於 `.pi/investment-adviser-board/portfolio-records/YYYY-MM-DD/`
- 檔名格式：
  - `portfolio-snapshot-user-YYYY-MM-DD.json`
  - `portfolio-snapshot-user-YYYY-MM-DD.md`
- `.pi/investment-adviser-board/portfolio-snapshot-user.json` 是最新 JSON 入口
- 本檔只作為人類可讀的 pointer 補充說明
- Agents 應優先使用 JSON pointer，再讀取對應的 dated JSON snapshot；Markdown 只作為補充註解與人工備忘
