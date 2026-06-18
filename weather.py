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
        icon_kind = "rain"
    elif pty == "2":
        status = "비/눈"
        icon_kind = "snow"
    elif pty == "3":
        status = "눈"
        icon_kind = "snow"
    elif pty == "4":
        status = "소나기"
        icon_kind = "shower"
    else:
        if sky == "1":
            status = "맑음"
            icon_kind = "sunny"
        elif sky == "3":
            status = "구름많음"
            icon_kind = "partly"
        elif sky == "4":
            status = "흐림"
            icon_kind = "cloudy"
        else:
            status = "날씨"
            icon_kind = "sunny"

    return tmp, status, icon_kind, pop, reh

def load_font(size):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
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

def draw_weather_icon(draw, kind, cx, cy):
    sun_fill = "#f4cf5a"
    sun_line = "#d8b13d"
    cloud_fill = "#edf2e6"
    cloud_outline = "#9cb37c"
    rain_color = "#7aa7d8"
    snow_color = "#8db2d6"

    def draw_cloud(x, y, scale=1.0):
        draw.ellipse((x - 26*scale, y - 2*scale, x - 4*scale, y + 18*scale), fill=cloud_fill, outline=cloud_outline)
        draw.ellipse((x - 6*scale, y - 12*scale, x + 18*scale, y + 12*scale), fill=cloud_fill, outline=cloud_outline)
        draw.ellipse((x + 10*scale, y - 2*scale, x + 32*scale, y + 18*scale), fill=cloud_fill, outline=cloud_outline)
        draw.rounded_rectangle((x - 26*scale, y + 6*scale, x + 32*scale, y + 22*scale), radius=int(10*scale), fill=cloud_fill, outline=cloud_outline)

    def draw_sun(x, y, r=10):
        draw.ellipse((x-r, y-r, x+r, y+r), fill=sun_fill, outline=sun_line)
        rays = [(0, -18), (13, -13), (18, 0), (13, 13), (0, 18), (-13, 13), (-18, 0), (-13, -13)]
        for dx, dy in rays:
            x1 = x + int(dx * 0.6)
            y1 = y + int(dy * 0.6)
            x2 = x + dx
            y2 = y + dy
            draw.line((x1, y1, x2, y2), fill=sun_line, width=2)

    if kind == "sunny":
        draw_sun(cx, cy, 10)

    elif kind == "partly":
        draw_sun(cx - 12, cy - 6, 8)
        draw_cloud(cx, cy, 1.0)

    elif kind == "cloudy":
        draw_cloud(cx, cy, 1.0)

    elif kind == "rain":
        draw_cloud(cx, cy - 4, 1.0)
        for offset in [-12, 0, 12]:
            draw.line((cx + offset, cy + 22, cx + offset - 3, cy + 32), fill=rain_color, width=3)

    elif kind == "shower":
        draw_sun(cx - 12, cy - 8, 7)
        draw_cloud(cx, cy - 2, 1.0)
        for offset in [-10, 2, 14]:
            draw.line((cx + offset, cy + 20, cx + offset - 3, cy + 30), fill=rain_color, width=3)

    elif kind == "snow":
        draw_cloud(cx, cy - 4, 1.0)
        for offset in [-12, 0, 12]:
            x = cx + offset
            y = cy + 28
            draw.line((x - 4, y, x + 4, y), fill=snow_color, width=2)
            draw.line((x, y - 4, x, y + 4), fill=snow_color, width=2)
            draw.line((x - 3, y - 3, x + 3, y + 3), fill=snow_color, width=2)
            draw.line((x - 3, y + 3, x + 3, y - 3), fill=snow_color, width=2)

    else:
        draw_sun(cx, cy, 10)
        
def create_image(values, base_date, base_time):
    width = 171
    height = 120

    tmp, status, icon_kind, pop, reh = weather_text_and_icon(values)

    img = Image.new("RGB", (width, height), "#d9ecbd")
    draw = ImageDraw.Draw(img)

    # 배경: 네이버 기본 위젯처럼 연하늘+연두 느낌
    bg_top = "#cfe8ef"
    bg_mid = "#dff0cf"
    bg_bottom = "#c9e3b0"

    for y in range(height):
        if y < 60:
            ratio = y / 60
            r = int(int(bg_top[1:3], 16) * (1 - ratio) + int(bg_mid[1:3], 16) * ratio)
            g = int(int(bg_top[3:5], 16) * (1 - ratio) + int(bg_mid[3:5], 16) * ratio)
            b = int(int(bg_top[5:7], 16) * (1 - ratio) + int(bg_mid[5:7], 16) * ratio)
        else:
            ratio = (y - 60) / 60
            r = int(int(bg_mid[1:3], 16) * (1 - ratio) + int(bg_bottom[1:3], 16) * ratio)
            g = int(int(bg_mid[3:5], 16) * (1 - ratio) + int(bg_bottom[3:5], 16) * ratio)
            b = int(int(bg_mid[5:7], 16) * (1 - ratio) + int(bg_bottom[5:7], 16) * ratio)
        draw.line((0, y, width, y), fill=(r, g, b))

    # 아주 옅은 종이/수채 느낌 점
    import random
    random.seed(7)
    for _ in range(120):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        alpha_color = random.choice(["#ffffff", "#eef7d8", "#b8d89b", "#c8e7ed"])
        draw.point((x, y), fill=alpha_color)

    # 둥근 테두리
    draw.rounded_rectangle(
        (1, 1, width - 2, height - 2),
        radius=8,
        outline="#a7cf7a",
        width=1
    )

    # 폰트
    font_top = load_font(17)
    font_bottom = load_font(13)

    text_dark = "#2f5f54"
    text_blue = "#2b8ed6"

    # 상태 영문 변환
    if icon_kind == "sunny":
        top_text = "SUNNY"
    elif icon_kind == "partly":
        top_text = "CLOUDY"
    elif icon_kind == "cloudy":
        top_text = "CLOUDY"
    elif icon_kind == "rain":
        top_text = "RAINY"
    elif icon_kind == "shower":
        top_text = "SHOWER"
    elif icon_kind == "snow":
        top_text = "SNOWY"
    else:
        top_text = status.upper()

    # 1구역: 상단 35px 중앙
    center_text(draw, top_text, 10, font_top, text_dark, width)

    # 2구역: 가운데 50px 중앙
    draw_weather_icon(draw, icon_kind, width // 2, 61)

    # 3구역: 하단 35px 중앙
    bottom_text = f"{AREA_NAME} {tmp}"
    bbox = draw.textbbox((0, 0), bottom_text, font=font_bottom)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) / 2
    y = 98

    draw.text((x, y), f"{AREA_NAME} ", font=font_bottom, fill=text_dark)

    area_bbox = draw.textbbox((0, 0), f"{AREA_NAME} ", font=font_bottom)
    area_width = area_bbox[2] - area_bbox[0]
    draw.text((x + area_width, y), f"{tmp}", font=font_bottom, fill=text_blue)

    img.save("weather.png")

def main():
    if not SERVICE_KEY:
        raise RuntimeError("KMA_SERVICE_KEY가 없습니다. GitHub Secrets를 확인하세요.")

    values, base_date, base_time = fetch_weather()
    create_image(values, base_date, base_time)

if __name__ == "__main__":
    main()
