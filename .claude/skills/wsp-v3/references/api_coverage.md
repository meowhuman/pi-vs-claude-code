# API Coverage & Limitations

## Engine Comparison

### Brave Search

- **Strengths**: Fast, good for English web/news, video search, API key rotation
- **Weaknesses**: Poor Chinese content indexing, doesn't index Chinese official media
- **Rate**: Free 2,000/month per key, 60/min

### Tavily

- **Strengths**: Deep content extraction, better than Brave for Chinese sites, domain filtering
- **Weaknesses**: Slower, smaller free tier, no news-specific endpoint
- **Rate**: Free 1,000/month, 40/min

### Bing (NEW in V3)

- **Strengths**: Best for Chinese mainland content among Western search engines, supports zh-CN market
- **Weaknesses**: Requires Azure subscription, free tier only 1,000/month
- **Rate**: Free 1,000/month, $3/1,000 after that
- **Setup**: Azure Portal → Create "Bing Search v7" resource → Get key

### Firecrawl (REMOVED in V3)

- **Reason**: Out of credit, was only used for "professional scraping" (Layer 3 of layered research)
- **Alternative**: Tavily extract can handle most scraping needs

## Forum API Coverage

| Forum       | API Type           | Rate Limit    | Auth Required |
| ----------- | ------------------ | ------------- | ------------- |
| Reddit      | JSON API           | Generous      | No (public)   |
| Hacker News | Firebase + Algolia | Unlimited     | No            |
| LIHKG       | Brave/Tavily site: | Engine limits | No            |
| PTT         | Brave/Tavily site: | Engine limits | No            |
| V2EX        | Brave/Tavily site: | Engine limits | No            |
| StockTwits  | Brave/Tavily site: | Engine limits | No            |
| Bitcointalk | Brave/Tavily site: | Engine limits | No            |
| 4chan /biz/ | Brave/Tavily site: | Engine limits | No            |

## China Coverage

Mainland Chinese sites are behind the Great Firewall (GFW). External search engines
can only index content that is publicly accessible from outside China.

### What works

- 知乎 (Zhihu) — Public Q&A content is well-indexed by Bing
- 雪球 (Xueqiu) — Investment discussions are accessible
- 豆瓣 (Douban) — Cultural content is accessible
- B站 (Bilibili) — Video metadata is indexed

### What doesn't work well

- 小红书 (Xiaohongshu) — Most content is app-only or login-required
- 微博 (Weibo) — Real-time tweets are hard to index from outside
- 百度贴吧 — Partially blocked from external crawlers

### Recommendations for deeper China coverage

1. **Bing API** (included in V3) — Best external option
2. **SerpAPI** — Can proxy Baidu search results (paid)
3. **Direct access** — VPN + browser for real-time content
4. **Jina Reader API** — Good at extracting Chinese web pages (free tier)
