# Ali Payroll Calculator

Ali (Alison Wong) 的舞蹈員薪酬計算工具。

## 資料位置
`/Users/terivercheung/Documents/AI/pi-vs-claude-code/doc/ali-admin/data/`
費率：`rates.json` | 巡迴資料：`tour-YYYY.json`

## 使用方式
`/ALI:ali-payroll [站號或城市] [年份(選填)]`

例如：
- `/ALI:ali-payroll 3` → 2026 第3站廣州薪酬
- `/ALI:ali-payroll 廣州 2027` → 2027年廣州站薪酬
- `/ALI:ali-payroll all` → 本年所有站合計

## 執行指示

1. 若用戶指定年份，載入 `tour-YYYY.json`；否則載入最新的 tour-*.json
2. 同時載入 `rates.json` 取得費率
3. 根據以下費率計算（優先用 rates.json，其次用 tour JSON 內的數字）：
   - Show fee: 標準 $5,500/場 × 場次；Puppet $3,000/場
   - 排練費: $120/hr × 該舞蹈員排練時數
   - Full Run: 標準 $2,500；Puppet $1,500

輸出格式：
```
=== 第X站 [城市] [日期] ===
舞蹈員       角色      Show Fee  排練費  Full Run  合計
------------------------------------------------------------
Tank 梁鉻宸  Dancer    $5,500    $2,400  $2,500    $10,400
Fatboy 梁業  Puppet    $3,000    $2,400  $1,500    $6,900
...
------------------------------------------------------------
合計舞蹈員薪酬：$XX,XXX
```

若輸入 `all`，顯示每站合計 + 全年總覽表格。
