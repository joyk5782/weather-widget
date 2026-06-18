import os
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

SERVICE_KEY = os.environ.get("KMA_SERVICE_KEY")

NX = "60"
NY = "127"
AREA_NAME = "서울"

def get_base_datetime():
    now = datetime.now() + timedelta(hours=9)  # GitHub Actions는 UTC라서 한국시간 보정

    base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    current = now.strftime("%H%M")

    available = [t for t in base_times if t <= current]

    if available:
        base_date = now.strftime("%Y%m%d")
        base_time = available[-1]
    else:
        yesterday = now - timedelta(days=1)
        base_date = yesterday.strftime("%Y%m%d")
        base_time = "2300"

    return base_date, base_time

def fetch_weather():
    base_date, base_time = get_base_datetime()

    url = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": NX,
        "ny": NY,
    }

    res = requests.get(url, params=params, timeout=20)
    res.raise_for_status()

    data = res.json()
    items = data["response"]["body"]["items"]["item"]

    target_date = items[0]["fcstDate"]
    target_time = items[0]["fcstTime"]

    values = {}
    for item in items:
        if item["fcstDate"] == target_date and item["fcstTime"] == target_time:
            values[item["category"]] = item["fcstValue"]

    return values, base_date, base_time

def weather_text_and_icon(values):
    tmp = values.get("TMP", "-")
    sky = values.get("SKY", "1")
    pty = values.get("PTY", "0")
    pop = values.get("POP", "-")
    reh = values.get("REH", "-")

    if pty == "1":
        status = "비"
        icon = "☔"
    elif pty == "2":
        status = "비/눈"
        icon = "🌨"
    elif pty == "3":
        status = "눈"
        icon = "❄"
    elif pty == "4":
        status = "소나기"
        icon = "🌦"
    else:
        if sky == "1":
            status = "맑음"
            icon = "☀"
        elif sky == "3":
            status = "구름많음"
            icon = "⛅"
        elif sky == "4":
            status = "흐림"
            icon = "☁"
        else:
            status = "날씨"
            icon = "☀"

    return tmp, status, icon, pop, reh

def load_font(size):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()

def center_text(draw, text, y, font, fill, image_width):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (image_width - text_width) / 2
    draw.text((x, y), text, font=font, fill=fill)

def create_image(values, base_date, base_time):
    width = 170
    height = 120

    tmp, status, icon, pop, reh = weather_text_and_icon(values)

    img = Image.new("RGB", (width, height), "#f4fae8")
    draw = ImageDraw.Draw(img)

    border = "#b7d98a"
    text_dark = "#426b1f"
    text_mid = "#7aa832"
    text_light = "#8cae5c"

    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=8, outline=border, width=2)

    font_title = load_font(12)
    font_icon = load_font(30)
    font_main = load_font(15)
    font_sub = load_font(10)

    center_text(draw, "TODAY WEATHER", 9, font_title, text_mid, width)
    center_text(draw, icon, 28, font_icon, text_dark, width)
    center_text(draw, f"{AREA_NAME} {tmp}℃ · {status}", 68, font_main, text_dark, width)
    center_text(draw, f"강수 {pop}% · 습도 {reh}%", 91, font_sub, text_light, width)

    img.save("weather.png")

def main():
    if not SERVICE_KEY:
        raise RuntimeError("KMA_SERVICE_KEY가 없습니다. GitHub Secrets를 확인하세요.")

    values, base_date, base_time = fetch_weather()
    create_image(values, base_date, base_time)

if __name__ == "__main__":
    main()
