# Cloudbet Trader — 個人知識庫

> 交易記錄和 API 使用心得

## API 連線狀態（最後驗證：2026-04-03）

### ✅ 全部已確認可用

| Endpoint | 說明 |
|----------|------|
| `GET /pub/v1/account/info` | 帳戶資訊（email, nickname） |
| `GET /pub/v1/account/currencies` | 啟用幣種列表 |
| `GET /pub/v1/account/currencies/{cur}/balance` | 餘額查詢 |
| `GET /pub/v2/odds/sports` | 所有運動列表 |
| `GET /pub/v2/odds/sports/soccer` | 足球分類結構 |
| `GET /pub/v2/odds/competitions/{key}` | 聯賽賽事列表 |
| `GET /pub/v2/odds/events/{id}` | 單場賽事完整賠率 |
| `POST /pub/v4/bets/place/straight` | ⚡ 下單（已驗證成功） |
| `GET /pub/v4/bets` | 注單歷史 |

**認證方式**：`X-API-Key: $CLOUDBET_API_TOKEN`（Header）
**Base URL**：`https://sports-api.cloudbet.com`

### ❌ 舊版已棄用
- `https://api.cloudbet.com/api/v1/*` — 全部已停用
- `POST /pub/v3/bets/place` — 舊版，會回 `invalid market URL`

### API 下單關鍵知識
- **必須用 `/pub/v4/`**（不是 `/pub/v3/`）
- `price` 必須是字串 `"1.80"` 不是數字
- `marketUrl` 直接用 odds feed 中的值（如 `soccer.match_odds/home`）
- `priceChange` 推薦 `SLIPPAGE_TOLERANCE` + `0.02`

---

## 已知 EPL 賽事 ID（2026-04-03 抓取）

| Event ID | 賽事 | 開賽時間（UTC） | 狀態 |
|----------|------|----------------|------|
| 33550037 | West Ham United vs Wolverhampton | 2026-04-10 20:00 | TRADING |
| 33550032 | Arsenal vs AFC Bournemouth | 2026-04-11 11:30 | TRADING |
| 33550035 | Brentford vs Everton | 2026-04-11 14:00 | TRADING |
| 33550026 | Liverpool vs Fulham | 2026-04-11 16:30 | TRADING |
| 33642701 | Crystal Palace vs Newcastle United | 2026-04-12 14:00 | TRADING |
| 33642702 | Nottingham Forest vs Aston Villa | 2026-04-12 14:00 | TRADING |
| 33550029 | Sunderland AFC vs Tottenham Hotspur | 2026-04-12 14:00 | TRADING |
| 33550031 | Chelsea vs Manchester City | 2026-04-12 16:30 | TRADING |
| 33550033 | Manchester United vs Leeds United | 2026-04-13 20:00 | TRADING |

> ⚠️ Event ID 會定期更新，查詢時需重新抓取

---

## Arsenal vs AFC Bournemouth 賠率快照（2026-04-03）

**賽事 ID**：33550032 | **開賽**：2026-04-11 11:30 UTC

| 市場 | 選項 | Cloudbet 賠率 |
|------|------|--------------|
| 全場勝負 | 主勝（Arsenal） | 1.39 |
| 全場勝負 | 平局 | 4.46 |
| 全場勝負 | 客勝（Bournemouth） | - |
| 讓球（AH） | 主隊 | 1.86 |
| 讓球（AH） | 客隊 | 1.85 |
| 大小球 | 大球（Over） | 1.75 |
| 大小球 | 小球（Under） | 1.97 |
| 兩隊進球 | 是 | 1.82 |
| 兩隊進球 | 否 | 1.88 |
| 平手注返（DNB） | 主勝 | 1.14 |
| 半場勝負 | 主勝 | 1.81 |
| 半場勝負 | 平局 | 2.51 |

---

## 聯賽 Competition Keys（已驗證）

| 聯賽 | Key |
|------|-----|
| 英超 | `soccer-england-premier-league` |
| FA Cup | `soccer-england-fa-cup` |

---

## 可用市場 Keys

`soccer.match_odds` / `soccer.asian_handicap` / `soccer.total_goals` /
`soccer.both_teams_to_score` / `soccer.draw_no_bet` / `soccer.correct_score` /
`soccer.halftime_fulltime_result` / `soccer.match_odds_period_first_half` /
`soccer.asian_handicap_period_first_half` / `soccer.team_total_goals`

---

## 交易記錄

| 日期 | 賽事 | 投注方向 | 賠率 | 金額 | 結果 | 復盤 |
|------|------|----------|------|------|------|------|
| 2026-04-03 | West Ham vs Wolves (EPL) | 主勝 (match_odds/home) | 1.80 | 0.1 USDT | 待結算 | API 首筆下單 ✅ |

**首筆 API 下單詳情**：
- betId: `e90976bb-6da9-4d5f-b632-c56fff6eca12`
- Event ID: `33550037`
- marketUrl: `soccer.match_odds/home`
- 賽事開賽: 2026-04-10 20:00 UTC

---

## 待辦事項

- [ ] 驗證其他聯賽 competition keys（西甲、德甲、意甲、法甲）
- [ ] 建立每週 EPL event_id 同步腳本
- [ ] 實作下單後查詢 bet 結果（GET /pub/v4/bets）
