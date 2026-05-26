"""
Parse and handle LINE text commands.

Supported commands (Thai + English):

  ราคา ทอง                          → gold price
  ราคา หุ้น [SYMBOL]                → stock price  (e.g. PTT, SCB)
  ราคา คริปโต [SYMBOL]              → crypto price (e.g. BTC, ETH)

  แจ้งเตือน ทอง [ราคา]              → alert: auto-detect direction
  แจ้งเตือน ทอง สูงกว่า [ราคา]     → alert when gold rises above price
  แจ้งเตือน ทอง ต่ำกว่า [ราคา]     → alert when gold drops below price
  แจ้งเตือน หุ้น [SYM] [ราคา]      → stock alert (same variants)
  แจ้งเตือน คริปโต [SYM] [ราคา]    → crypto alert (same variants)

  ดูแจ้งเตือน                        → list active alerts
  ลบแจ้งเตือน [id]                  → delete alert by id
  ลบแจ้งเตือนทั้งหมด                → delete all alerts

  ช่วยเหลือ / help                   → help
"""

from app import database as db
from app.line import messaging as msg
from app.scrapers import gold, stock, crypto
from app.scrapers.crypto import SUPPORTED as CRYPTO_SUPPORTED


# ── Keyword sets ────────────────────────────────────────────────────────────────

_CMD_PRICE  = {"ราคา", "price", "ราคาทอง"}
_CMD_ALERT  = {"แจ้งเตือน", "alert", "ตั้งแจ้งเตือน", "set"}
_CMD_LIST   = {"ดูแจ้งเตือน", "listalerts", "alerts", "แจ้งเตือนทั้งหมด"}
_CMD_DELETE = {"ลบแจ้งเตือน", "deletealert", "delete", "ยกเลิกแจ้งเตือน"}
_CMD_HELP   = {"ช่วยเหลือ", "help", "วิธีใช้", "คำสั่ง"}

_ASSET_GOLD   = {"ทอง", "gold", "ทองคำ"}
_ASSET_STOCK  = {"หุ้น", "stock", "หลักทรัพย์"}
_ASSET_CRYPTO = {"คริปโต", "crypto", "คริปต์", "cryptocurrency"}

_COND_ABOVE = {"สูงกว่า", "มากกว่า", "above", ">", ">="}
_COND_BELOW = {"ต่ำกว่า", "น้อยกว่า", "below", "<", "<="}


# ── Entry point ─────────────────────────────────────────────────────────────────

def handle(user_id: str, reply_token: str, text: str):
    parts = text.strip().split()
    if not parts:
        return

    cmd = parts[0].lower()

    if cmd in _CMD_PRICE or cmd in _ASSET_GOLD:
        _cmd_price(user_id, reply_token, parts)
    elif cmd in _CMD_ALERT:
        _cmd_set_alert(user_id, reply_token, parts)
    elif cmd in _CMD_LIST:
        _cmd_list_alerts(user_id, reply_token)
    elif cmd in _CMD_DELETE or text.startswith("ลบแจ้งเตือนทั้งหมด"):
        _cmd_delete_alert(user_id, reply_token, parts, text)
    elif cmd in _CMD_HELP:
        _cmd_help(reply_token)
    else:
        msg.reply(reply_token, [msg.text_msg(
            "ไม่รู้จักคำสั่งนี้ 🤔\nพิมพ์ 'ช่วยเหลือ' เพื่อดูคำสั่งที่ใช้ได้"
        )])


# ── Command handlers ─────────────────────────────────────────────────────────────

def _cmd_price(user_id: str, reply_token: str, parts: list[str]):
    # ราคา ทอง | ราคา หุ้น PTT | ราคา คริปโต BTC | ราคาทอง (1 word)
    if len(parts) == 1 or (len(parts) >= 2 and parts[1].lower() in _ASSET_GOLD):
        data = gold.fetch()
        if data:
            msg.reply(reply_token, [msg.flex_msg("ราคาทองคำ", msg.build_gold_bubble(data))])
        else:
            msg.reply(reply_token, [msg.text_msg("ดึงราคาทองไม่ได้ในขณะนี้ ลองใหม่อีกครั้ง")])

    elif len(parts) >= 2 and parts[1].lower() in _ASSET_STOCK:
        if len(parts) < 3:
            msg.reply(reply_token, [msg.text_msg("กรุณาระบุชื่อหุ้น เช่น: ราคา หุ้น PTT")])
            return
        sym = parts[2].upper()
        msg.reply(reply_token, [msg.text_msg(f"⏳ กำลังดึงราคาหุ้น {sym}...")])
        data = stock.fetch(sym)
        if data:
            msg.push(user_id, [msg.flex_msg(f"ราคาหุ้น {data.symbol}", msg.build_stock_bubble(data))])
        else:
            msg.push(user_id, [msg.text_msg(
                f"ไม่พบข้อมูลหุ้น '{sym}'\n"
                "ตรวจสอบชื่อย่อหุ้น SET ให้ถูกต้อง เช่น PTT, SCB, KBANK, AOT"
            )])

    elif len(parts) >= 2 and parts[1].lower() in _ASSET_CRYPTO:
        if len(parts) < 3:
            msg.reply(reply_token, [msg.text_msg(
                f"กรุณาระบุชื่อเหรียญ เช่น: ราคา คริปโต BTC\n"
                f"เหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
            )])
            return
        sym = parts[2].upper()
        data = crypto.fetch(sym)
        if data:
            msg.reply(reply_token, [msg.flex_msg(f"ราคา {data.symbol}", msg.build_crypto_bubble(data))])
        else:
            msg.reply(reply_token, [msg.text_msg(
                f"ไม่รองรับเหรียญ '{sym}'\n"
                f"เหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
            )])
    else:
        msg.reply(reply_token, [msg.text_msg(
            "รูปแบบคำสั่ง:\n"
            "• ราคา ทอง\n"
            "• ราคา หุ้น [ชื่อหุ้น]\n"
            "• ราคา คริปโต [ชื่อเหรียญ]"
        )])


def _cmd_set_alert(user_id: str, reply_token: str, parts: list[str]):
    # แจ้งเตือน ทอง 45000
    # แจ้งเตือน ทอง สูงกว่า 45000
    # แจ้งเตือน หุ้น PTT 40
    # แจ้งเตือน คริปโต BTC 3500000

    if len(parts) < 3:
        msg.reply(reply_token, [msg.text_msg(
            "รูปแบบ: แจ้งเตือน [ทอง/หุ้น/คริปโต] [ราคา]\n"
            "ตัวอย่าง: แจ้งเตือน ทอง 45000\n"
            "ตัวอย่าง: แจ้งเตือน หุ้น PTT สูงกว่า 40"
        )])
        return

    asset_word = parts[1].lower()

    if asset_word in _ASSET_GOLD:
        _save_alert(user_id, reply_token, "gold", None, parts[2:])

    elif asset_word in _ASSET_STOCK:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือน หุ้น [ชื่อหุ้น] [ราคา]")])
            return
        _save_alert(user_id, reply_token, "stock", parts[2].upper(), parts[3:])

    elif asset_word in _ASSET_CRYPTO:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือน คริปโต [ชื่อเหรียญ] [ราคา]")])
            return
        sym = parts[2].upper()
        if sym not in CRYPTO_SUPPORTED:
            msg.reply(reply_token, [msg.text_msg(
                f"ไม่รองรับเหรียญ '{sym}'\nเหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
            )])
            return
        _save_alert(user_id, reply_token, "crypto", sym, parts[3:])
    else:
        msg.reply(reply_token, [msg.text_msg(
            "ระบุประเภทสินทรัพย์: ทอง, หุ้น, หรือ คริปโต\n"
            "เช่น: แจ้งเตือน ทอง 45000"
        )])


def _save_alert(user_id: str, reply_token: str, asset_type: str,
                symbol: str | None, remaining: list[str]):
    # remaining: ['45000'] | ['สูงกว่า', '45000'] | ['ต่ำกว่า', '45000']
    condition: str | None = None
    price_str: str | None = None

    if len(remaining) == 1:
        price_str = remaining[0]
    elif len(remaining) == 2:
        word = remaining[0].lower()
        if word in _COND_ABOVE:
            condition = "above"
        elif word in _COND_BELOW:
            condition = "below"
        else:
            msg.reply(reply_token, [msg.text_msg(
                f"ไม่รู้จักเงื่อนไข '{remaining[0]}'\n"
                "ใช้ 'สูงกว่า' หรือ 'ต่ำกว่า'"
            )])
            return
        price_str = remaining[1]
    else:
        msg.reply(reply_token, [msg.text_msg("รูปแบบไม่ถูกต้อง ดูคำสั่งได้ที่ 'ช่วยเหลือ'")])
        return

    try:
        target_price = float(price_str.replace(",", ""))
        if target_price <= 0:
            raise ValueError
    except ValueError:
        msg.reply(reply_token, [msg.text_msg(f"ราคา '{price_str}' ไม่ถูกต้อง กรุณาใส่ตัวเลข")])
        return

    # Auto-detect direction when no condition given
    if condition is None:
        current = _get_current_price(asset_type, symbol)
        if current is None:
            msg.reply(reply_token, [msg.text_msg("ดึงราคาปัจจุบันไม่ได้ กรุณาลองใหม่")])
            return
        if abs(current - target_price) / target_price < 0.005:
            msg.reply(reply_token, [msg.text_msg(
                f"ราคาปัจจุบัน ({current:,.2f} ฿) ใกล้เคียงกับราคาเป้าหมายมาก\n"
                "กรุณาระบุเงื่อนไข: สูงกว่า หรือ ต่ำกว่า"
            )])
            return
        condition = "above" if current < target_price else "below"

    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (user_id, asset_type, asset_symbol, target_price, condition_type) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user_id, asset_type, symbol, target_price, condition),
    )
    alert_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    asset_labels = {"gold": "ทองคำ (แท่งซื้อ)", "stock": f"หุ้น {symbol}", "crypto": f"คริปโต {symbol}"}
    cond_labels  = {"above": "สูงกว่าหรือเท่ากับ", "below": "ต่ำกว่าหรือเท่ากับ"}

    msg.reply(reply_token, [msg.text_msg(
        f"✅ ตั้งแจ้งเตือน #{alert_id} สำเร็จ!\n\n"
        f"สินทรัพย์ : {asset_labels[asset_type]}\n"
        f"เงื่อนไข  : {cond_labels[condition]}\n"
        f"ราคา      : {target_price:,.2f} ฿\n\n"
        "จะแจ้งเตือนเมื่อราคาถึงเป้าหมาย 🔔"
    )])


def _cmd_list_alerts(user_id: str, reply_token: str):
    conn = db.get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, asset_type, asset_symbol, target_price, condition_type, created_at "
        "FROM alerts WHERE user_id = %s AND is_active = 1 ORDER BY id",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        msg.reply(reply_token, [msg.text_msg("ยังไม่มีการแจ้งเตือนที่ตั้งไว้ 📋")])
        return

    asset_labels = {"gold": "ทองคำ", "stock": "หุ้น", "crypto": "คริปโต"}
    cond_labels  = {"above": "สูงกว่า", "below": "ต่ำกว่า"}
    lines = [f"📋 แจ้งเตือนของคุณ ({len(rows)} รายการ)\n"]
    for r in rows:
        sym = f" {r['asset_symbol']}" if r["asset_symbol"] else ""
        asset = f"{asset_labels[r['asset_type']]}{sym}"
        cond  = cond_labels[r["condition_type"]]
        price = float(r["target_price"])
        lines.append(f"#{r['id']} {asset} → {cond} {price:,.2f} ฿")

    lines.append("\nพิมพ์ 'ลบแจ้งเตือน [หมายเลข]' เพื่อลบ")
    msg.reply(reply_token, [msg.text_msg("\n".join(lines))])


def _cmd_delete_alert(user_id: str, reply_token: str, parts: list[str], full_text: str):
    if "ทั้งหมด" in full_text:
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET is_active = 0 WHERE user_id = %s AND is_active = 1", (user_id,))
        count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        msg.reply(reply_token, [msg.text_msg(f"🗑️ ลบแจ้งเตือนทั้งหมด {count} รายการแล้ว")])
        return

    if len(parts) < 2:
        msg.reply(reply_token, [msg.text_msg("ระบุหมายเลขที่ต้องการลบ เช่น: ลบแจ้งเตือน 3")])
        return

    try:
        alert_id = int(parts[1])
    except ValueError:
        msg.reply(reply_token, [msg.text_msg(f"หมายเลข '{parts[1]}' ไม่ถูกต้อง")])
        return

    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE alerts SET is_active = 0 WHERE id = %s AND user_id = %s AND is_active = 1",
        (alert_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if affected:
        msg.reply(reply_token, [msg.text_msg(f"🗑️ ลบแจ้งเตือน #{alert_id} เรียบร้อย")])
    else:
        msg.reply(reply_token, [msg.text_msg(f"ไม่พบแจ้งเตือน #{alert_id} หรืออาจถูกลบไปแล้ว")])


def _cmd_help(reply_token: str):
    help_text = (
        "💡 คำสั่งที่ใช้ได้\n\n"
        "📈 ดูราคา:\n"
        "• ราคา ทอง\n"
        "• ราคา หุ้น PTT\n"
        "• ราคา คริปโต BTC\n\n"
        "🔔 ตั้งแจ้งเตือน:\n"
        "• แจ้งเตือน ทอง 45000\n"
        "• แจ้งเตือน ทอง สูงกว่า 45000\n"
        "• แจ้งเตือน ทอง ต่ำกว่า 44000\n"
        "• แจ้งเตือน หุ้น PTT 40\n"
        "• แจ้งเตือน คริปโต BTC 3500000\n\n"
        "📋 จัดการแจ้งเตือน:\n"
        "• ดูแจ้งเตือน\n"
        "• ลบแจ้งเตือน [หมายเลข]\n"
        "• ลบแจ้งเตือนทั้งหมด\n\n"
        f"💰 คริปโตที่รองรับ:\n{', '.join(CRYPTO_SUPPORTED)}"
    )
    msg.reply(reply_token, [msg.text_msg(help_text)])


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _get_current_price(asset_type: str, symbol: str | None) -> float | None:
    if asset_type == "gold":
        data = gold.fetch()
        return data.bar_buy if data else None
    if asset_type == "stock":
        data = stock.fetch(symbol)
        return data.price if data else None
    if asset_type == "crypto":
        data = crypto.fetch(symbol)
        return data.price_thb if data else None
    return None
