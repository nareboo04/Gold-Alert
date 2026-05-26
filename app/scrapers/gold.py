import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional


@dataclass
class GoldPrice:
    bar_buy: float
    bar_sell: float
    ornament_buy: float
    ornament_sell: float
    change_amount: str
    change_status: str   # 'up' | 'down' | 'flat'
    updated_date: str
    updated_time: str


def fetch() -> Optional[GoldPrice]:
    try:
        resp = requests.get("https://xn--42cah7d0cxcvbbb9x.com/", timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find("table").find_all("tr", class_="trline")

        def price(row, col) -> float:
            tds = row.find_all("td")
            if len(tds) > col:
                try:
                    return float(tds[col].text.strip().replace(",", ""))
                except ValueError:
                    return 0.0
            return 0.0

        def text(row, col) -> str:
            tds = row.find_all("td")
            return tds[col].text.strip() if len(tds) > col else ""

        bar_buy      = price(rows[1], 1) if len(rows) > 1 else 0.0
        bar_sell     = price(rows[1], 2) if len(rows) > 1 else 0.0
        ornament_buy  = price(rows[2], 1) if len(rows) > 2 else 0.0
        ornament_sell = price(rows[2], 2) if len(rows) > 2 else 0.0

        change_status = "flat"
        if len(rows) > 3:
            if rows[3].find("span", class_="css-sprite-up"):
                change_status = "up"
            elif rows[3].find("span", class_="css-sprite-down"):
                change_status = "down"

        change_amount = text(rows[3], 2) if len(rows) > 3 else ""
        updated_date  = text(rows[4], 0) if len(rows) > 4 else ""
        updated_time  = text(rows[4], 1) if len(rows) > 4 else ""

        return GoldPrice(bar_buy, bar_sell, ornament_buy, ornament_sell,
                         change_amount, change_status, updated_date, updated_time)
    except Exception as e:
        print(f"[gold] fetch error: {e}")
        return None
