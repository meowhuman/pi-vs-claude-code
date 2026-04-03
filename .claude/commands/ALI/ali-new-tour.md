# Ali New Tour Setup

為 Ali (ARTLIKE HK) 設定全新巡迴演出資料，自動生成 JSON + 全套 CSV。

## 腳本位置
`/Users/terivercheung/Documents/AI/pi-vs-claude-code/doc/ali-admin/scripts/generate-tour.py`

## 費率參考
`/Users/terivercheung/Documents/AI/pi-vs-claude-code/doc/ali-admin/data/rates.json`

## 使用方式
直接執行指令即可啟動互動式設定：

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code
python3 doc/ali-admin/scripts/generate-tour.py
```

## 執行指示

當用戶輸入 `/ALI:ali-new-tour`，執行以下步驟：

1. **執行腳本**：用 Bash 工具執行上述 python3 指令
   - 腳本會互動式收集：巡迴名稱、客戶、各站城市/日期/場次/舞蹈員/排練時數
   - 自動從上一個巡迴的 JSON 載入舞蹈員名單供重用

2. **自動生成以下檔案**：
   - `data/tour-YYYY.json` — 完整巡迴資料庫
   - `exports/tour-YYYY/01-tour-summary.csv`
   - `exports/tour-YYYY/02-payroll-all-stations.csv`
   - `exports/tour-YYYY/03-dancer-earnings-summary.csv`
   - `exports/tour-YYYY/04-payment-tracker.csv`

3. **完成後更新指令路徑**：提示用戶如需在其他 `/ALI:` 指令中查詢新巡迴，
   只需告知 "查 2027 巡迴" — 系統會自動找 `tour-2027.json`

## 費率更新提示
如需更新費率（加價等），只需修改：
`doc/ali-admin/data/rates.json`
所有新巡迴計算自動採用新費率，舊巡迴 JSON 保留原始數字不受影響。

## 快速輸入技巧
- 舞蹈員選擇輸入 `all` = 沿用上站全部名單
- 排練時數輸入單一數字 = 所有人相同時數
- 空白行 = 完成當前輸入
