require('dotenv').config();
const { ethers } = require('ethers');
const axios = require('axios');

// 偽裝瀏覽器
axios.defaults.headers.common['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
axios.defaults.headers.common['Origin'] = 'https://polymarket.com';
axios.defaults.headers.common['Referer'] = 'https://polymarket.com/';

async function trade() {
    try {
        console.log("🚀 最終方案 - ethers.js v5 + EIP-712");
        console.log("=" + "=".repeat(50));
        console.log();

        // 1. Wallet
        const pk = process.env.POLYGON_PRIVATE_KEY;
        const wallet = new ethers.Wallet(pk);
        const addr = wallet.address;

        console.log("🔑 Wallet:", addr);
        console.log("   Private:", pk.substring(0, 10) + "..." + pk.slice(-8));
        console.log();

        // 2. Market data
        const market = await axios.get('https://clob.polymarket.com/markets/0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e').then(r => r.data);
        console.log("📊 Market:", market.question);

        let tokenId = null, price = 0.44;
        for (const t of market.tokens) {
            if (t.outcome.toLowerCase() === 'yes') {
                tokenId = t.token_id;
                price = t.price;
                break;
            }
        }
        console.log("📦 Token:", tokenId.substring(0, 50) + "...");
        console.log("   Price: $", price);
        console.log();

        // 3. Order
        const amount = 0.1;
        const size = amount / price;
        const nonce = Math.floor(Date.now() / 1000);
        const priceInt = Math.round(price * 1000000);
        const sizeInt = Math.round(size * 1000000);

        console.log("💰 Order:");
        console.log("   Price: $", price);
        console.log("   Size: ", size.toFixed(6), "shares");
        console.log("   Total: $", amount, "USDC");
        console.log();

        // 4. EIP-712
        console.log("🔐 Creating EIP-712 signature...");

        const domain = {
            name: "Polymarket CLOB",
            version: "1",
            chainId: 137,
            verifyingContract: "0x4d8dc65db31aa7e5a06029fbece3720d8aa56d5d"
        };

        const types = {
            Order: [
                { name: "maker", type: "address" },
                { name: "token_id", type: "uint256" },
                { name: "price", type: "uint256" },
                { name: "size", type: "uint256" },
                { name: "side", type: "uint256" },
                { name: "nonce", type: "uint256" },
                { name: "expiration", type: "uint256" },
                { name: "fee_rate_bps", type: "uint256" }
            ]
        };

        const message = {
            maker: addr,
            token_id: tokenId,
            price: priceInt.toString(),
            size: sizeInt.toString(),
            side: 0, // BUY
            nonce: nonce,
            expiration: 0,
            fee_rate_bps: 0
        };

        const signature = await wallet._signTypedData(domain, types, message);
        console.log("   Signature:", signature.substring(0, 60) + "...");
        console.log();

        // 5. POST
        const payload = {
            maker: addr,
            token_id: tokenId,
            price: priceInt.toString(),
            size: sizeInt.toString(),
            side: 0,
            nonce: nonce.toString(),
            expiration: "0",
            fee_rate_bps: "0",
            signature: signature,
            signature_type: 0
        };

        console.log("📤 POSTing to CLOB...");
        const response = await axios.post(
            'https://clob.polymarket.com/order',
            JSON.stringify(payload),
            { headers: { 'Content-Type': 'application/json', ...axios.defaults.headers.common } }
        );

        console.log("\n✅ SUCCESS!");
        console.log("Response:", JSON.stringify(response.data, null, 2));
        return true;

    } catch (err) {
        console.error("\n❌ FAILED:", err.message);
        if (err.response) {
            console.error("Status:", err.response.status);
            console.error("Response:", JSON.stringify(err.response.data, null, 2));
        }
        return false;
    }
}

trade().then(success => {
    console.log(success ? "\n✅ Completed" : "\n❌ Failed");
    process.exit(success ? 0 : 1);
});
