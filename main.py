import time
import datetime
from app import database as db
from app.config import ALERT_CHECK_INTERVAL, DAILY_REPORT_HOUR
from app.services.alert_checker import run as check_alerts, send_daily_gold_report


def get_all_user_ids() -> list[str]:
    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r[0] for r in rows]


def main():
    print("[main] initializing database...")
    db.init_db()
    print(f"[main] alert check every {ALERT_CHECK_INTERVAL}s | daily report at {DAILY_REPORT_HOUR}:00")

    last_daily_date: datetime.date | None = None

    while True:
        now = datetime.datetime.now()

        # Daily gold report
        if now.hour == DAILY_REPORT_HOUR and now.minute < (ALERT_CHECK_INTERVAL // 60 + 1):
            if last_daily_date != now.date():
                print("[main] sending daily gold report")
                send_daily_gold_report(get_all_user_ids())
                last_daily_date = now.date()

        # Alert check
        try:
            print(f"[main] checking alerts at {now.strftime('%H:%M:%S')}")
            check_alerts()
        except Exception as e:
            print(f"[main] alert check error: {e}")

        time.sleep(ALERT_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
