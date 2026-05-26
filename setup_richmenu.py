#!/usr/bin/env python3
"""
Register LINE Rich Menu with emoji icons (Twemoji).
pip install Pillow requests python-dotenv
python setup_richmenu.py
"""
import io
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("กรุณาติดตั้ก Pillow: pip install Pillow")

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("LINE_TOKEN", "")
if not TOKEN:
    sys.exit("[error] LINE_TOKEN not set in .env")

BASE      = "https://api.line.me/v2/bot"
BASE_DATA = "https://api-data.line.me/v2/bot"
HEADERS   = {"Authorization": f"Bearer {TOKEN}"}

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H   = 2500, 843          # LINE half-size rich menu
COLS   = 3
CW, CH = W // COLS, H // 2  # 833 × 421 per cell

# ── Button config ─────────────────────────────────────────────────────────────
#  (label, command, card_color, twemoji_codepoint)
BUTTONS = [
    ("ราคาทอง",   "ราคา ทอง",          "#92530a", "1f4b0"),  # 💰
    ("หุ้นไทย",   "ราคา หุ้น ",         "#0f3d8c", "1f4c8"),  # 📈
    ("หุ้นเมกา",  "ราคา หุ้นเมกา ",    "#0c2f6e", "1f1fa-1f1f8"),  # 🇺🇸
    ("คริปโต",    "ราคา คริปโต BTC",   "#4a1280", "1f48e"),  # 💎
    ("แจ้งเตือน", "ดูแจ้งเตือน",        "#0f5c2e", "1f514"),  # 🔔
    ("ช่วยเหลือ", "ช่วยเหลือ",          "#1e3a5f", "2753"),   # ❓
]

BG       = "#0d1117"   # background (GitHub dark)
EMOJI_SZ = 160         # emoji size in px
RADIUS   = 28          # card corner radius
GAP      = 14          # gap between cards

CACHE = Path(".cache/emoji")
CACHE.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

_EMOJI_CDNS = [
    "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{cp}.png",
    "https://cdn.jsdelivr.net/npm/@jdecked/twemoji@latest/assets/72x72/{cp}.png",
]


def fetch_emoji(codepoint: str) -> Image.Image | None:
    """Download Twemoji PNG and cache locally, trying multiple CDNs."""
    path = CACHE / f"{codepoint}.png"
    if not path.exists():
        for cdn in _EMOJI_CDNS:
            url = cdn.format(cp=codepoint)
            try:
                r = requests.get(url, timeout=8)
                r.raise_for_status()
                path.write_bytes(r.content)
                break
            except Exception:
                continue
        else:
            print(f"  [warn] emoji {codepoint}: ดาวน์โหลดไม่ได้จากทุก CDN")
            return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Thonburi.ttc",                              # macOS
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",         # Linux
        "/usr/share/fonts/thai/Laksaman.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def paste_emoji(canvas: Image.Image, emoji: Image.Image,
                cx: int, cy: int, size: int):
    """Paste emoji centered at (cx, cy)."""
    e = emoji.resize((size, size), Image.LANCZOS)
    x = cx - size // 2
    y = cy - size // 2
    canvas.paste(e, (x, y), e)


def draw_card(canvas: Image.Image, x0: int, y0: int,
              color: str, emoji: Image.Image | None, label: str,
              font: ImageFont.FreeTypeFont):
    """Draw one button card."""
    # ── Rounded card ──
    layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Subtle gradient: slightly lighter shade on top half
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    top_color    = (min(r + 30, 255), min(g + 30, 255), min(b + 30, 255), 255)
    bottom_color = (r, g, b, 255)
    for row in range(GAP, CH - GAP):
        ratio = row / CH
        rc = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        gc = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        bc = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        d.line([(GAP, row), (CW - GAP, row)], fill=(rc, gc, bc, 255))

    # Clip to rounded rect (draw rounded rect on top as mask)
    mask = Image.new("L", (CW, CH), 0)
    md   = ImageDraw.Draw(mask)
    md.rounded_rectangle([GAP, GAP, CW - GAP, CH - GAP], radius=RADIUS, fill=255)
    layer.putalpha(mask)

    # Subtle top highlight (1px line)
    d.rounded_rectangle([GAP, GAP, CW - GAP, GAP + 2], radius=RADIUS,
                        fill=(255, 255, 255, 60))

    canvas.paste(layer, (x0, y0), layer)

    # ── Emoji ──
    draw  = ImageDraw.Draw(canvas)
    inner = CH - GAP * 2
    content_h = EMOJI_SZ + 16 + 72  # emoji + gap + text
    start_y   = y0 + GAP + (inner - content_h) // 2

    emoji_cy = start_y + EMOJI_SZ // 2
    if emoji:
        paste_emoji(canvas, emoji, x0 + CW // 2, emoji_cy, EMOJI_SZ)
    text_y = start_y + EMOJI_SZ + 16

    # ── Label ──
    bbox = draw.textbbox((0, 0), label, font=font)
    tw   = bbox[2] - bbox[0]
    draw.text(
        (x0 + (CW - tw) // 2, text_y),
        label, fill="#ffffff", font=font,
    )


# ── Image builder ─────────────────────────────────────────────────────────────

def build_image() -> bytes:
    print("  กำลังดาวน์โหลด emoji...")
    emojis = []
    for _, _, _, cp in BUTTONS:
        e = fetch_emoji(cp)
        emojis.append(e)
        status = "✓" if e else "✗"
        print(f"    {status} {cp}")

    canvas = Image.new("RGBA", (W, H), BG)
    font   = load_font(68)

    for i, ((label, _, color, _), emoji) in enumerate(zip(BUTTONS, emojis)):
        col = i % COLS
        row = i // COLS
        draw_card(canvas, col * CW, row * CH, color, emoji, label, font)

    # Horizontal divider between rows
    d = ImageDraw.Draw(canvas)
    d.line([(0, H // 2), (W, H // 2)], fill="#ffffff18", width=2)

    # Convert to RGB JPEG
    result = Image.new("RGB", (W, H), BG)
    result.paste(canvas, mask=canvas.split()[3])

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ── Rich menu structure ───────────────────────────────────────────────────────

def build_structure() -> dict:
    areas = []
    for i, (_, cmd, _, _) in enumerate(BUTTONS):
        col = i % COLS
        row = i // COLS
        areas.append({
            "bounds": {"x": col * CW, "y": row * CH, "width": CW, "height": CH},
            "action": {"type": "message", "text": cmd},
        })
    return {
        "size":        {"width": W, "height": H},
        "selected":    True,
        "name":        "Gold Alert Menu",
        "chatBarText": "เมนู 📋",
        "areas":       areas,
    }


# ── LINE API ──────────────────────────────────────────────────────────────────

def delete_all_menus():
    r = requests.get(f"{BASE}/richmenu/list", headers=HEADERS, timeout=10)
    for m in r.json().get("richmenus", []):
        mid = m["richMenuId"]
        requests.delete(f"{BASE}/richmenu/{mid}", headers=HEADERS, timeout=10)
        print(f"  ลบเมนูเก่า: {mid}")


def main():
    print("─── LINE Rich Menu Setup ───────────────────────\n")

    print("1) ลบ rich menu เก่า...")
    delete_all_menus()

    print("\n2) สร้าง structure...")
    r = requests.post(
        f"{BASE}/richmenu",
        headers={**HEADERS, "Content-Type": "application/json"},
        data=json.dumps(build_structure()),
        timeout=10,
    )
    if not r.ok:
        sys.exit(f"[error] {r.status_code}: {r.text}")
    menu_id = r.json()["richMenuId"]
    print(f"  richMenuId: {menu_id}")

    print("\n3) สร้างรูปเมนู...")
    img_bytes = build_image()
    print(f"  ขนาด: {len(img_bytes) // 1024} KB")

    print("\n4) อัปโหลดรูป...")
    r = requests.post(
        f"{BASE_DATA}/richmenu/{menu_id}/content",
        headers={**HEADERS, "Content-Type": "image/jpeg"},
        data=img_bytes,
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"[error] upload: {r.status_code}: {r.text}")

    print("\n5) ตั้งเป็น default menu...")
    r = requests.post(
        f"{BASE}/user/all/richmenu/{menu_id}",
        headers=HEADERS, timeout=10,
    )
    if not r.ok:
        sys.exit(f"[error] set default: {r.status_code}: {r.text}")

    print(f"\n✅ เสร็จแล้ว! (id: {menu_id})")
    print("   เปิดแชทบอทใน LINE เพื่อดูเมนู\n")


if __name__ == "__main__":
    main()
