# Ali Payment Tracker

追蹤各巡迴收付款狀態。

## 資料位置
`/Users/terivercheung/Documents/AI/pi-vs-claude-code/doc/ali-admin/data/`

## 使用方式
- `/ALI:ali-payment` → 最新巡迴付款狀態
- `/ALI:ali-payment 2026` → 指定年份
- `/ALI:ali-payment overdue` → 逾期未收
- `/ALI:ali-payment upcoming` → 30天內到期
- `/ALI:ali-payment [站號] received [日期]` → 標記收款（更新 JSON）

## 執行指示

載入指定（或最新）tour-YYYY.json，對照今天日期顯示：

```
=== 付款追蹤 (今天: YYYY-MM-DD) ===

⚠️ 逾期未收：
  第X站 城市 — 截止 YYYY-MM-DD（逾期 N 天）$XXX,XXX

⏰ 即將到期 (30天內)：
  第X站 城市 — 截止 YYYY-MM-DD（還有 N 天）$XXX,XXX

✅ 已收款：（列出）

📅 未來收款：（列出）

待收總額：$X,XXX,XXX
```

標記收款時，更新 JSON 的 `payment_status` 為 `"received"`，`payment_received` 為日期。
