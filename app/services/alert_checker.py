"""
Check all active alerts against current market prices and fire notifications.
Groups alerts by (asset_type, symbol) so each asset is fetched only once per cycle.
"""

from collections import defaultdict
from app import database as db
from app.line import messaging as msg
from app.scrapers import gold, stock, crypto


def run():
    conn = db.get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, user_id, asset_type, asset_symbol, target_price, condition_type "
        "FROM alerts WHERE is_active = 1"
    )
    alerts = cursor.fetchall()
    cursor.close()
    conn.close()

    if not alerts:
        return

    # Group by asset so each price is fetched once
    groups: dict[tuple, list] = defaultdict(list)
    for alert in alerts:
        key = (alert["asset_type"], alert["asset_symbol"])
        groups[key].append(alert)

    triggered_ids: list[int] = []

    for (asset_type, symbol), group in groups.items():
        current_price = _fetch_price(asset_type, symbol)
        if current_price is None:
            continue

        for alert in group:
            target    = float(alert["target_price"])
            condition = alert["condition_type"]
            fired = (condition == "above" and current_price >= target) or \
                    (condition == "below" and current_price <= target)

            if fired:
                triggered_ids.append(alert["id"])
                _notify(alert, current_price)

    if triggered_ids:
        conn = db.get_conn()
        cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(triggered_ids))
        cursor.execute(f"UPDATE alerts SET is_active = 0 WHERE id IN ({placeholders})", triggered_ids)
        conn.commit()
        cursor.close()
        conn.close()


def send_daily_gold_report(users: list[str]):
    data = gold.fetch()
    if not data:
        print("[daily report] failed to fetch gold price")
        return

    bubble = msg.build_gold_bubble(data)
    for user_id in users:
        msg.push(user_id, [msg.flex_msg("ราคาทองคำประจำวัน", bubble)])


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _fetch_price(asset_type: str, symbol: str | None) -> float | None:
    try:
        if asset_type == "gold":
            data = gold.fetch()
            return data.bar_buy if data else None
        if asset_type == "stock":
            data = stock.fetch(symbol)
            return data.price if data else None
        if asset_type == "crypto":
            data = crypto.fetch(symbol)
            return data.price_thb if data else None
    except Exception as e:
        print(f"[alert checker] price fetch error ({asset_type} {symbol}): {e}")
    return None


def _notify(alert: dict, current_price: float):
    try:
        bubble = msg.build_alert_triggered_bubble(alert, current_price)
        asset_type = alert["asset_type"]
        symbol = alert.get("asset_symbol") or ""
        labels = {"gold": "ทองคำ", "stock": f"หุ้น {symbol}", "crypto": f"คริปโต {symbol}"}
        alt = f"แจ้งเตือน {labels.get(asset_type, '')} ถึงราคาเป้าหมาย!"
        msg.push(alert["user_id"], [msg.flex_msg(alt, bubble)])
        print(f"[alert] fired #{alert['id']} → user {alert['user_id']}")
    except Exception as e:
        print(f"[alert checker] notify error: {e}")
