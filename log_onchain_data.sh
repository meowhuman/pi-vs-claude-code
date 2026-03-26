#!/bin/bash
# 每小時記錄一次鏈上數據

LOG_DIR="$HOME/onchain-logs"
mkdir -p "$LOG_DIR"

while true; do
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    DATE=$(date +%Y-%m-%d)
    
    # 記錄到以日期為名的檔案
    echo "=== $TIMESTAMP ===" >> "$LOG_DIR/chain_tvl_$DATE.log"
    echo "=== $TIMESTAMP ===" >> "$LOG_DIR/bridge_flows_$DATE.log"
    
    # 這裡可以加入實際的 API 呼叫
    # curl -s "https://api.llama.fi/chains" >> "$LOG_DIR/chain_tvl_$DATE.log"
    
    sleep 3600  # 每小時記錄一次
done
