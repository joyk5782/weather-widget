import os
import math
import random
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



def draw_wobbly_line(draw, p1, p2, fill, width=2, jitter=1.2, steps=6):
    x1, y1 = p1
    x2, y2 = p2
    points = []
    for i in range(steps + 1):
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if 0 < i < steps:
            x += random.uniform(-jitter, jitter)
            y += random.uniform(-jitter, jitter)
        points.append((x, y))
    draw.line(points, fill=fill, width=width)


def draw_wobbly_circle(draw, cx, cy, r, outline, width=2, jitter=1.2, points_count=24):
    points = []
    for i in range(points_count + 1):
        ang = (math.pi * 2) * i / points_count
        rr = r + random.uniform(-jitter, jitter)
        x = cx + math.cos(ang) * rr
        y = cy + math.sin(ang) * rr
        points.append((x, y))
    draw.line(points, fill=outline, width=width)


def draw_sketch_sun(draw, cx, cy, ink):
    random.seed(11)

    # 얼굴 원
    draw_wobbly_circle(draw, cx, cy, 11, outline=ink, width=2, jitter=0.8)

    # 눈
    draw.ellipse((cx - 5, cy - 2, cx - 3, cy, ), fill=ink)
    draw.ellipse((cx + 3, cy - 2, cx + 5, cy, ), fill=ink)

    # 입
    draw.arc((cx - 5, cy + 1, cx + 5, cy + 7), start=15, end=165, fill=ink, width=1)

    # 광선
    rays = [
        (0, -22), (9, -19), (18, -10), (22, 0), (18, 10),
        (9, 19), (0, 22), (-9, 19), (-18, 10), (-22, 0),
        (-18, -10), (-9, -19)
    ]
    for dx, dy in rays:
        length_scale = random.uniform(0.88, 1.08)
        x1 = cx + dx * 0.62
        y1 = cy + dy * 0.62
        x2 = cx + dx * length_scale
        y2 = cy + dy * length_scale
        draw_wobbly_line(draw, (x1, y1), (x2, y2), fill=ink, width=2, jitter=0.7, steps=4)


def draw_sketch_cloud(draw, cx, cy, ink):
    random.seed(17)
    draw.arc((cx - 28, cy - 2, cx - 6, cy + 18), start=180, end=360, fill=ink, width=2)
    draw.arc((cx - 10, cy - 12, cx + 10, cy + 12), start=180, end=360, fill=ink, width=2)
    draw.arc((cx + 6, cy - 4, cx + 28, cy + 16), start=180, end=360, fill=ink, width=2)
    draw_wobbly_line(draw, (cx - 28, cy + 8), (cx + 28, cy + 8), fill=ink, width=2, jitter=0.6, steps=7)


def draw_weather_icon(draw, kind, cx, cy):
    ink = "#466f88"

    if kind == "sunny":
        draw_sketch_sun(draw, cx, cy, ink)

    elif kind == "partly":
        draw_sketch_sun(draw, cx - 10, cy - 3, ink)
        draw_sketch_cloud(draw, cx + 4, cy + 6, ink)

    elif kind == "cloudy":
        draw_sketch_cloud(draw, cx, cy + 2, ink)

    elif kind == "rain":
        draw_sketch_cloud(draw, cx, cy, ink)
        for offset in [-12, 0, 12]:
            draw_wobbly_line(draw, (cx + offset, cy + 18), (cx + offset - 2, cy + 28), fill=ink, width=2, jitter=0.6, steps=4)

    elif kind == "shower":
        draw_sketch_sun(draw, cx - 10, cy - 5, ink)
        draw_sketch_cloud(draw, cx + 4, cy + 4, ink)
        for offset in [-10, 2, 14]:
            draw_wobbly_line(draw, (cx + offset, cy + 20), (cx + offset - 2, cy + 30), fill=ink, width=2, jitter=0.6, steps=4)

    elif kind == "snow":
        draw_sketch_cloud(draw, cx, cy, ink)
        for offset in [-12, 0, 12]:
            x = cx + offset
            y = cy + 25
            draw_wobbly_line(draw, (x - 4, y), (x + 4, y), fill=ink, width=1, jitter=0.4, steps=2)
            draw_wobbly_line(draw, (x, y - 4), (x, y + 4), fill=ink, width=1, jitter=0.4, steps=2)

    else:
        draw_sketch_sun(draw, cx, cy, ink)
        
def create_image(values, base_date, base_time):
    width = 171
    height = 120

    tmp, status, icon_kind, pop, reh = weather_text_and_icon(values)

    img = Image.new("RGB", (width, height), "#dcebd3")
    draw = ImageDraw.Draw(img)

    # 배경: 수채+종이 느낌
    base_colors = ["#d7e8d0", "#d8ebe8", "#d9efd2", "#cfe4ee", "#d8eac7"]
    draw.rectangle((0, 0, width, height), fill="#d9eacb")

    random.seed(5)
    for _ in range(18):
        color = random.choice(base_colors)
        x = random.randint(-10, width - 20)
        y = random.randint(-10, height - 20)
        w = random.randint(28, 60)
        h = random.randint(18, 38)
        draw.ellipse((x, y, x + w, y + h), fill=color)

    # 잔점 텍스처
    for _ in range(110):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        c = random.choice(["#edf5ea", "#cfe5c7", "#d7ebf3"])
        draw.point((x, y), fill=c)

    # 아주 약한 외곽
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=7, outline="#bdd6c7", width=1)

    # 폰트 / 색상
    font_top = load_font(18)
    font_bottom = load_font(14)

    text_dark = "#2b2b2b"
    text_blue = "#2a88d4"

    # 상태 영문
    if icon_kind == "sunny":
        top_text = "SUNNY"
    elif icon_kind == "partly":
        top_text = "PARTLY"
    elif icon_kind == "cloudy":
        top_text = "CLOUDY"
    elif icon_kind == "rain":
        top_text = "RAINY"
    elif icon_kind == "shower":
        top_text = "SHOWER"
    elif icon_kind == "snow":
        top_text = "SNOWY"
    else:
        top_text = "WEATHER"

    # 상단 35
    center_text(draw, top_text, 8, font_top, text_dark, width)

    # 중단 50
    draw_weather_icon(draw, icon_kind, width // 2, 57)

    # 하단 35
    bottom_y = 98
    city_text = f"{AREA_NAME} "
    temp_text = f"{tmp}"

    city_bbox = draw.textbbox((0, 0), city_text, font=font_bottom)
    temp_bbox = draw.textbbox((0, 0), temp_text, font=font_bottom)

    city_w = city_bbox[2] - city_bbox[0]
    temp_w = temp_bbox[2] - temp_bbox[0]
    total_w = city_w + temp_w

    start_x = (width - total_w) / 2

    draw.text((start_x, bottom_y), city_text, font=font_bottom, fill=text_dark)
    draw.text((start_x + city_w, bottom_y), temp_text, font=font_bottom, fill=text_blue)

    img.save("weather.png")
    

def main():
    if not SERVICE_KEY:
        raise RuntimeError("KMA_SERVICE_KEY가 없습니다. GitHub Secrets를 확인하세요.")

    values, base_date, base_time = fetch_weather()
    create_image(values, base_date, base_time)

if __name__ == "__main__":
    main()
