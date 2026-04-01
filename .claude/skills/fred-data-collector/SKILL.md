---
name: FRED Data Collector
description: Collects macroeconomic data from Federal Reserve Economic Data (FRED) API. Use when user needs GDP, inflation, unemployment, interest rates, or other economic indicators. Automatically handles API authentication, data fetching, and storage.
---

# FRED Data Collector

Automated collection of macroeconomic data from Federal Reserve Economic Data (FRED) API.

---

## Prerequisites

### 1. Get FRED API Key
```bash
# Visit: https://fred.stlouisfed.org/docs/api/api_key.html
# Register for free account and get API key
```

### 2. Set Environment Variable
```bash
# Add to your shell profile (~/.bash_profile, ~/.zshrc, etc.)
export FRED_API_KEY='your_api_key_here'

# Or create .env file in project root
# echo "FRED_API_KEY=your_key" > .env
```

### 3. Install Dependencies
```bash
pip install fredapi pandas requests
```

---

## Workflow

### Step 1: Initialize Collector
```bash
# From project root, run the collection script
python3 .claude/skills/fred-data-collector/scripts/collect_fred.py
```

### Step 2: Select Data Categories
The script will prompt you to choose:
1. **Core Economic Indicators** (GDP, CPI, Unemployment)
2. **Interest Rates** (Fed Funds, Treasury yields)
3. **Labor Market** (NFP, Jobless claims)
4. **Custom Series** (enter specific FRED series IDs)

### Step 3: Data Storage
Collected data is automatically saved to:
- `datas/fred/` - Raw data files
- `datas/fred/summary/` - Summary reports
- Format: CSV (readable by Excel) and Parquet (efficient storage)

### Step 4: Generate Report
A markdown summary is created with:
- Latest values for each indicator
- Month-over-month changes
- Year-over-year changes
- Visual trend indicators (↑↓→)

---

## Usage Examples

### Example 1: Collect Core Economic Data

User request:
```
Get latest GDP, inflation, and unemployment data
```

You would:
1. Run the collection script:
   ```bash
   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py
   ```
2. Select option 1 (Core Economic Indicators)
3. The script automatically fetches:
   - Real GDP (GDP)
   - CPI (CPIAUCSL)
   - Unemployment rate (UNRATE)
   - Core PCE (PCEPILFE)
   - Fed Funds rate (DFF)
4. Review generated summary report at:
   `datas/fred/summary/economic_indicators_YYYY-MM-DD.md`

### Example 2: Monitor Interest Rates

User request:
```
Track Treasury yields and Fed policy
```

You would:
1. Run collection script with interest rate focus:
   ```bash
   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --category rates
   ```
2. The script collects:
   - Fed Funds Effective Rate (DFF)
   - 2-Year Treasury (DGS2)
   - 10-Year Treasury (DGS10)
   - 30-Year Treasury (DGS30)
   - Yield curve spread (calculated)
3. Check for yield curve inversions (warning if 10Y-2Y < 0)
4. Save data to `datas/fred/rates/`

### Example 3: Custom Series Collection

User request:
```
Get industrial production and retail sales data
```

You would:
1. Run script with custom series option:
   ```bash
   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --custom
   ```
2. Enter FRED series IDs when prompted:
   ```
   Enter series IDs (comma-separated): INDPRO, RSAFS
   ```
3. Add descriptions:
   ```
   INDPRO description: Industrial Production Index
   RSAFS description: Retail Sales
   ```
4. Data is collected and stored with custom naming
5. Use the `--save-config` option to save this setup for future use

---

## Available Data Series

### Core Economic Indicators
| Name | FRED ID | Frequency | Importance |
|------|---------|-----------|------------|
| Real GDP | GDP | Quarterly | 🔥🔥🔥🔥🔥 |
| Real GDP Growth | A191RL1Q225SBEA | Quarterly | 🔥🔥🔥🔥🔥 |
| CPI (All Items) | CPIAUCSL | Monthly | 🔥🔥🔥🔥🔥 |
| Core CPI | CPILFESL | Monthly | 🔥🔥🔥🔥🔥 |
| PCE Price Index | PCEPI | Monthly | 🔥🔥🔥🔥🔥 |
| Core PCE | PCEPILFE | Monthly | 🔥🔥🔥🔥🔥 |
| Unemployment Rate | UNRATE | Monthly | 🔥🔥🔥🔥🔥 |
| Nonfarm Payrolls | PAYEMS | Monthly | 🔥🔥🔥🔥🔥 |
| Initial Claims | ICSA | Weekly | 🔥🔥🔥🔥 |

### Interest Rates
| Name | FRED ID | Frequency |
|------|---------|-----------|
| Fed Funds Rate | DFF | Daily |
| 2-Year Treasury | DGS2 | Daily |
| 10-Year Treasury | DGS10 | Daily |
| 30-Year Treasury | DGS30 | Daily |
| 3-Month Treasury | DTB3 | Daily |

### Money Supply & Credit
| Name | FRED ID |
|------|---------|
| M1 Money Stock | M1SL |
| M2 Money Stock | M2SL |
| Fed Balance Sheet | WALCL |
| Bank Credit | TOTBKCR |

### Additional Recommended Series
```python
# Housing Market
'MEDLISPRI'  # Median Sales Price of Houses Sold
'UNDRGRT'    # 30-Year Fixed Rate Mortgage

# Inflation Expectations
'MICH'       # University of Michigan Inflation Expectations
'T5YIE'      # 5-Year Breakeven Inflation Rate

# Labor Market (Additional)
'JTSJOL'     # Job Openings
'PERMCS'     # Continuing Claims
```

---

## Advanced Usage

### Batch Collection
```bash
# Create a config file with desired series
echo '{"series": ["GDP", "CPIAUCSL", "UNRATE", "DGS10"]}' > my_config.json

# Run with config
python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --config my_config.json
```

### Automated Scheduling
```bash
# Add to crontab for daily collection
crontab -e

# Add line:
0 7 * * * cd /path/to/project && python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --auto
```

### Integration with Analysis
```python
# Load collected data for analysis
import pandas as pd

gdp = pd.read_csv('datas/fred/GDP_history.csv', index_col=0, parse_dates=True)
cpi = pd.read_csv('datas/fred/CPIAUCSL_history.csv', index_col=0, parse_dates=True)

# Calculate derived metrics
gdp_growth = gdp.pct_change(4) * 100  # YoY growth
cpi_yoy = cpi.pct_change(12) * 100
```

---

## Error Handling

### Common Issues

**1. Invalid API Key**
```
Error: 403 Forbidden - Authentication failed
Solution: Check FRED_API_KEY environment variable is set correctly
```

**2. Series Not Found**
```
Error: Series ID 'XXXX' not found
Solution: Verify series ID at https://fred.stlouisfed.org/
```

**3. Rate Limit Exceeded**
```
Error: 429 Too Many Requests
Solution: Free tier allows 120 requests/hour. Add delays or upgrade account.
```

**4. Missing Data**
```
Warning: Series has NaN values for recent dates
Solution: Some series (like GDP) have reporting delays. Check FRED website for release schedule.
```

---

## Output Format

### CSV Structure
```
Date       | GDP      | CPIAUCSL | UNRATE | DGS10
-----------|----------|----------|--------|--------
2025-10-01 | 28423.91 | 314.861  | 4.1    | 4.15
2025-09-01 | 28423.91 | 314.175  | 4.2    | 4.08
```

### Summary Report Example
```markdown
# Economic Indicators Summary - 2025-12-06

## Key Metrics
- **Unemployment Rate**: 4.1% (↓ from 4.2%)
- **CPI (YoY)**: 2.4% (↑ from 2.3%)
- **Fed Funds Rate**: 5.25-5.50% range
- **10Y Treasury**: 4.15% (↓ 5bp)

## Trend Analysis
- Labor market cooling but still tight
- Inflation stabilizing near Fed target
- Yield curve remains inverted (10Y-2Y = -0.45%)
```

---

## Configuration

### Environment Variables
```bash
# Required
export FRED_API_KEY='your_key_here'

# Optional
export FRED_DATA_DIR='./datas/fred'  # Default: ./datas/fred
export FRED_LOG_LEVEL='INFO'         # Default: INFO
```

### Configuration File
```json
{
  "api_key": "your_key",
  "data_directory": "./datas/fred",
  "series": {
    "GDP": {
      "name": "Real GDP",
      "category": "economic"
    }
  },
  "auto_collect": ["CPIAUCSL", "UNRATE", "DGS10"]
}
```

---

## Dependencies

```python
# /// script
# dependencies = [
#   "fredapi>=0.5.1",
#   "pandas>=2.0.0",
#   "requests>=2.28.0",
#   "click>=8.0.0"  # For CLI interface
# ]
# ///
```

---

## License

MIT License - Free to use and modify

---

**Last Updated**: 2025-12-06
**API Version**: FRED v1
