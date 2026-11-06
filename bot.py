import asyncio
import time
from datetime import datetime
import schedule
import requests
from bs4 import BeautifulSoup
import re
import threading
import os

from flask import Flask
from pyrobale import Client

# ================== تنظیمات ==================
BOT_TOKEN = "1436036233:o6TSrXuG9yq1XpP7ujDDBpD8orszsYgShw0"
CHAT_ID   = "5344687354"
# =============================================

# 🖼️ لیست لینک‌های عکس (به ترتیب چرخشی)
IMAGE_URLS = [
    "https://i.ibb.co/tMkg5SkR/image2.jpg",
    "https://i.ibb.co/wFDwB3fj/image3.jpg",
    "https://i.ibb.co/ymZ91Fdy/image4.jpg",
    "https://i.ibb.co/B5Z2PKCC/image5.jpg",
]

# شمارنده برای انتخاب به ترتیب
image_index = 0

# 🧪 حالت تست: هر ۱ ساعت
TEST_MODE = True
SEND_TIMES = ["10:00", "18:00"]

# ================== وب‌سرور برای Render ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "GoldBot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# =========================================================

def get_next_image():
    """به ترتیب عکس بعدی رو برمی‌گردونه و وقتی به آخر رسید، از اول شروع می‌کنه"""
    global image_index
    url = IMAGE_URLS[image_index]
    image_index = (image_index + 1) % len(IMAGE_URLS)
    return url

def get_price_from_estjt():
    url = "https://www.estjt.ir/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()

        pattern = r"طلا\s*۱۸\s*عیار[\s\S]*?([\d۰-۹]+[٫,\.][\d۰-۹٫,\.]+)"
        match = re.search(pattern, page_text)

        if match:
            price_str = match.group(1)
            price_str = price_str.replace("٫", "").replace(",", "").replace(".", "").strip()
            persian = "۰۱۲۳۴۵۶۷۸۹"
            english = "0123456789"
            price_str = price_str.translate(str.maketrans(persian, english))
            price = int(price_str)
            print(f"[PRICE] From estjt.ir: {price:,} toman")
            return price
        else:
            print("[WARN] Pattern not found in estjt.ir")
            return None
    except Exception as e:
        print(f"[ERROR] estjt.ir: {e}")
        return None

def round_to_thousand(value):
    """سه رقم آخر رو صفر می‌کنه (مثلاً 27,218,415 → 27,218,000)"""
    return (int(value) // 1000) * 1000

def calculate_and_build_text(gheimat):
    payeh = gheimat + 100_000

    nim_gerami  = payeh * 1.07  * 0.5
    yek_gerami  = payeh * 1.05  * 1
    do_gerami   = payeh * 1.04  * 2
    se_gerami   = payeh * 1.04  * 3
    panj_gerami = payeh * 1.036 * 5

    # سه رقم آخر صفر می‌شه
    payeh_fmt = f"{round_to_thousand(payeh):,.0f}"
    nim       = f"{round_to_thousand(nim_gerami):,.0f}"
    yek       = f"{round_to_thousand(yek_gerami):,.0f}"
    do        = f"{round_to_thousand(do_gerami):,.0f}"
    se        = f"{round_to_thousand(se_gerami):,.0f}"
    panj      = f"{round_to_thousand(panj_gerami):,.0f}"

    text = (
        f"💸 قیمت امروز شمش های گلدمایند به ازای هرگرم طلا ی عیار ۷۵۰\n"
        f"✔️در وزن های ۰/۵ تا ۵ گرم موجود است\n"
        f"💸 قیمت لحظه ای یک گرم طلا : {payeh_fmt}\n\n"
        f"✓ ۰/۵گرمی گلدمایند : {nim}ت\n\n"
        f"✓ ۱ گرم : {yek}ت\n\n"
        f"✓ ۲ گرم : {do}ت\n\n"
        f"✓ ۳ گرم : {se} ت\n\n"
        f"✓ ۵ گرم : {panj} ت\n\n"
        f"💎ارتباط با ما:\n"
        f"@GOLDMIND_ADMIN\n\n"
        f"☎️تماس:09121202331 قاسمی\n\n"
        f"🆔: ble.ir/join/2pqRkYqS17\n"
        f"#شمش\n"
        f"#گلدمایند"
    )
    return text

async def send_to_channel():
    try:
        gheimat = get_price_from_estjt()
        if gheimat is None:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [ERROR] Price not fetched, sending cancelled")
            return

        text = calculate_and_build_text(gheimat)
        client = Client(BOT_TOKEN)

        image_url = get_next_image()
        print(f"[IMG] Selected: {image_url}")

        try:
            await client.send_photo(
                chat_id=CHAT_ID,
                photo=image_url,
                caption=text,
            )
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [OK] Photo + text sent")
        except Exception as photo_error:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [WARN] Photo failed ({photo_error}) -> trying text only")
            await client.send_message(
                chat_id=CHAT_ID,
                text=text,
            )
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [OK] Text only sent")

    except Exception as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [ERROR] {e}")

def job():
    asyncio.run(send_to_channel())

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    print(f"[WEB] Server running on port {os.environ.get('PORT', 8080)}")

    if TEST_MODE:
        schedule.every(1).hours.do(job)
        print("[TEST] Test mode: sending every 1 hour")
    else:
        for t in SEND_TIMES:
            schedule.every().day.at(t).do(job)
        print(f"[BOT] Started. Send times: {SEND_TIMES}")

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()