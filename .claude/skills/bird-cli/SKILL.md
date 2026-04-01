---
name: bird-cli
description: Post tweets, reply, read, and search X/Twitter via Bird CLI on VPS. Auth pre-configured on tcvps (root@43.129.246.234). Run all commands via SSH.
---

# Bird CLI — X/Twitter via VPS

Bird CLI (`@steipete/bird`) 安裝在 tcvps (`root@43.129.246.234`)，認證已存放於 `~/.bird_auth`。
所有指令透過 SSH 執行。

## 認證狀態

- ✅ 已設定：`~/.bird_auth` 含 `AUTH_TOKEN` + `CT0`
- 執行方式：`source ~/.bird_auth` 後帶 `--auth-token` 和 `--ct0` flags

## 指令格式

所有 bird 指令的 SSH wrapper：

```bash
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" <command>"
```

## 常用指令

### 搜尋推文

```bash
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" search 'BTC 市場'"
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" search 'Fed rate' --limit 10"
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" search '#crypto' --json"
```

### 讀取推文

```bash
# 用 URL
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" read https://x.com/user/status/1234567890"

# 用 ID
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" read 1234567890"

# 讀取回覆串
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" replies 1234567890"
```

### 發推文

```bash
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" tweet 'Hello from Bird CLI'"
```

### 回覆推文

```bash
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" reply 1234567890 'Great point!'"
```

### 附加媒體

```bash
ssh root@43.129.246.234 "source ~/.bird_auth && bird --auth-token \"\$AUTH_TOKEN\" --ct0 \"\$CT0\" tweet 'Check this chart' --media /path/to/chart.png --alt 'BTC price chart'"
```

## 常用選項

| Flag | 說明 |
|------|------|
| `--json` | JSON 格式輸出（方便解析） |
| `--limit N` | 限制搜尋結果數量 |
| `--plain` | 純文字輸出（無 emoji/顏色） |
| `--quote-depth N` | 引用推文深度（預設 1，0 停用） |

## 基礎設施

- **Bird 位置**：`/usr/bin/bird` → `/usr/lib/node_modules/@steipete/bird/dist/cli.js`
- **版本**：`bird 0.8.0`
- **認證檔**：`/root/.bird_auth`（已在 `.bashrc` 中 source）
- **VPS**：`root@43.129.246.234`（alias: `tcvps`）

## 更新認證

若 token 過期，需到 X.com 取得新的 `auth_token` 和 `ct0` cookies，
更新 `/root/.bird_auth` 的 `AUTH_TOKEN` 和 `CT0` 值。
