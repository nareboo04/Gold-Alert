import requests
from dataclasses import dataclass
from typing import Optional

COIN_IDS: dict[str, str] = {
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "BNB":   "binancecoin",
    "XRP":   "ripple",
    "SOL":   "solana",
    "ADA":   "cardano",
    "DOGE":  "dogecoin",
    "MATIC": "matic-network",
    "DOT":   "polkadot",
    "AVAX":  "avalanche-2",
    "LTC":   "litecoin",
    "LINK":  "chainlink",
    "UNI":   "uniswap",
    "ATOM":  "cosmos",
    "NEAR":  "near",
}

SUPPORTED = list(COIN_IDS.keys())


@dataclass
class CryptoPrice:
    symbol: str
    price_thb: float
    price_usd: float
    change_24h: float


def fetch(symbol: str) -> Optional[CryptoPrice]:
    sym = symbol.upper()
    coin_id = COIN_IDS.get(sym)
    if not coin_id:
        return None
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "thb,usd",
                "include_24hr_change": "true",
            },
            timeout=10,
        )
        data = resp.json().get(coin_id, {})
        if not data:
            return None
        return CryptoPrice(
            symbol=sym,
            price_thb=data.get("thb", 0.0),
            price_usd=data.get("usd", 0.0),
            change_24h=data.get("thb_24h_change", 0.0),
        )
    except Exception as e:
        print(f"[crypto] {symbol} error: {e}")
        return None
