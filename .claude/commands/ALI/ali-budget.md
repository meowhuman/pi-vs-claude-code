# Ali Budget Overview

Ali (ARTLIKE HK) 財務總覽。

## 資料位置
`/Users/terivercheung/Documents/AI/pi-vs-claude-code/doc/ali-admin/data/`

## 使用方式
- `/ALI:ali-budget` → 最新巡迴全年財務
- `/ALI:ali-budget 2026` → 指定年份
- `/ALI:ali-budget [站號] 2026` → 單站利潤分析

## 執行指示

載入指定年份（或最新）的 tour-YYYY.json + rates.json，計算：

```
=== [巡迴名稱] — 財務總覽 ===

收入（向客戶收）：
  第1站 城市    $XXX,XXX
  ...
  合計：$X,XXX,XXX

支出（付給舞蹈員 + 場地）：
  舞蹈員薪酬合計：$XXX,XXX
  Studio 租金合計：$XXX,XXX
  總支出：$XXX,XXX

Ali 編舞費：$XXX,XXX（各站合計）
Admin 費：$XX,XXX（各站合計）
估算淨利：$XXX,XXX
```
