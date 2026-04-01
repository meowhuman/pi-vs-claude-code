# VPS Setup Guide for sta-v2

## System Requirements

TA-Lib requires the native C library. Install it **before** `uv sync`.

### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install -y libta-lib-dev
```

### CentOS / RHEL / Amazon Linux

```bash
# Option A: from source (most reliable)
wget https://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib && ./configure --prefix=/usr && make && sudo make install && cd ..

# Option B: EPEL (CentOS 7)
sudo yum install ta-lib-devel
```

### macOS (Homebrew)

```bash
brew install ta-lib
```

---

## Install & Setup

```bash
# 1. Clone / copy skill to VPS
scp -r /path/to/skills/sta-v2 user@vps:/opt/sta-v2

# 2. Enter skill directory
cd /opt/sta-v2

# 3. Create .env with API key
echo "TIINGO_API_KEY=your_key_here" > .env

# 4. Install Python deps via uv
uv sync

# 5. Verify
uv run scripts/main.py health
```

---

## Running on VPS

Always run from the skill root:

```bash
cd /opt/sta-v2
uv run scripts/main.py indicators AAPL
uv run scripts/main.py combined TSLA 180d
uv run scripts/main.py momentum NVDA
```

---

## .env Variables

| Variable         | Required | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `TIINGO_API_KEY` | Yes      | Get free key at https://api.tiingo.com |

---

## Troubleshooting

**`talib` import error after `uv sync`**
→ TA-Lib C library not installed. Run system install step above first, then `uv sync` again.

**`TIINGO_API_KEY not configured`**
→ Create `.env` file in skill root with the key.

**Permission errors**
→ `chmod +x scripts/main.py` if needed.
