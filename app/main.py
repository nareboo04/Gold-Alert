import time
import datetime
from app import database as db
from app.config import ALERT_CHECK_INTERVAL
from app.services.alert_checker import check_price_alerts, check_scheduled_alerts


def main():
    print("[main] initializing database...")
    db.init_db()
    print(f"[main] schedule check: every 60s | price check: every {ALERT_CHECK_INTERVAL}s")

    last_price_check = 0.0

    while True:
        now = datetime.datetime.now()

        # ── Schedule alerts: check every minute ──────────────────────────────
        try:
            check_scheduled_alerts()
        except Exception as e:
            print(f"[main] schedule check error: {e}")

        # ── Price alerts: check every ALERT_CHECK_INTERVAL ───────────────────
        if time.monotonic() - last_price_check >= ALERT_CHECK_INTERVAL:
            try:
                print(f"[main] checking price alerts at {now.strftime('%H:%M:%S')}")
                check_price_alerts()
            except Exception as e:
                print(f"[main] price check error: {e}")
            last_price_check = time.monotonic()

        time.sleep(60)


if __name__ == "__main__":
    main()
