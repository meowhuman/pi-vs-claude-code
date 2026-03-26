# Drip Music Decision Board — Just Shortcuts

## 基本指令

```bash
# 完整董事會（7 位成員）
just ext-drip-board

# 快速審議（Revenue + Contrarian，2 分鐘）
just ext-drip-board-quick

# 市場推廣決策（Brand + Marketing + Content + Contrarian）
just ext-drip-board-marketing

# 資助/政府關係決策（Grants + Revenue + International + Contrarian）
just ext-drip-board-grants

# 藝人/節目決策（Brand + International + Revenue + Contrarian）
just ext-drip-board-programming
```

## 手動選擇 Preset

```bash
# 在 Pi 內使用 /board-preset 命令切換成員組合
just ext-drip-board
# 然後輸入: /board-preset
```

## 直接指定 Preset（環境變數）

```bash
BOARD_PRESET=full               just ext-drip-board   # 全體 8 人
BOARD_PRESET=programming        just ext-drip-board   # 藝人節目
BOARD_PRESET=marketing-campaign just ext-drip-board   # 市場推廣
BOARD_PRESET=grants-funding     just ext-drip-board   # 資助申請
BOARD_PRESET=creative           just ext-drip-board   # 創意方向
BOARD_PRESET=quick              just ext-drip-board   # 快速 2 人
```

## Board Member 一覽

| 成員 | 角色 | 預設啟用 |
|------|------|---------|
| brand | 品牌與創意總監 | ✓ |
| marketing | 市場推廣與受眾發展 | ✓ |
| grants | 資助與政府關係 | ✓ |
| international | 海外藝人/夥伴策略師 | ✓ |
| content | 內容與文案總監 | ✓ |
| revenue | 財務現實主義策略師 | ✓ |
| contrarian | 魔鬼代言人 | ✓ |
| community | 社區與教育策略師 | ○（選擇性） |

## Memo 記錄位置

```
.pi/drip-board/memos/<slug>-<timestamp>.md
```

每份備忘錄包含：
- 原始 Brief
- CEO 框架分析
- 所有成員完整立場
- 最終決策建議
- 分歧與張力
- 下一步行動

## 快速啟動流程

1. `just ext-drip-board`
2. 輸入你的策略問題（或 paste brief）
3. 使用 `board_begin` 工具開始審議
4. 讀取備忘錄，在 `.pi/drip-board/memos/` 查閱完整紀錄

## Pi 內部命令

```
/board-preset    切換 preset（選擇出席成員）
/board-status    查看所有成員狀態
```
