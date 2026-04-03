# Ali Roster Viewer

查看各巡迴各站舞蹈員名單。

## 資料位置
`/Users/terivercheung/Documents/AI/pi-vs-claude-code/doc/ali-admin/data/`

## 使用方式
- `/ALI:ali-roster` → 最新巡迴所有站名單
- `/ALI:ali-roster [站號] [年份]` → 指定站詳細名單
- `/ALI:ali-roster Tank` → Tank 參加哪些站
- `/ALI:ali-roster compare 3 4` → 比較兩站換人情況

## 執行指示

載入指定（或最新）tour-YYYY.json：

單站格式：
```
=== 第X站 城市 日期 ===
#  舞蹈員     角色
1  Tank 梁鉻宸  Dancer
...
14 Fatboy 梁業  Puppet
（共X人）
```

全覽：表格形式，橫=各站城市，縱=舞蹈員，✓=參與 -=不在

換人比較：標記 +新加入 / -替換出
