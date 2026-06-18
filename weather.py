import os
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

# =========================
# 기본 설정
# =========================
SERVICE_KEY = os.environ.get("KMA_SERVICE_KEY")

NX = "60"
NY = "127"
AREA_NAME = "서울"

ASSET_DIR = "assets"
FONT_PATH = os.path.join(ASSET_DIR, "fonts", "handwriting.ttf")
OUTPUT_PATH = "weather.png"

# 텍스트 위치/크기
FONT_SIZE = 22
TEXT_Y = 225   # 필요하면 220~238 사이로 조절
CITY_COLOR = "#3c3328"
TEMP_COLOR = "#2d8bd8"

# 이미지 파일 매핑
IMAGE_MAP = {
    "sunny": "sunny.png",
    "partly": "partly.png",
    "cloudy": "cloudy.png",
    "rainy": "rainy.png",
    "snowy": "snowy.png",
}

KST = timezone(timedelta(hours=9))


# =========================
# 발표 시각 계산
# =========================
def get_base_datetime():
    now = datetime.now(KST)

    # 단기예보 발표시각
    base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    current_hhmm = now.strftime("%H%M")

    available = [t for t in base_times if t <= current_hhmm]

    if available:
        base_date = now.strftime("%Y%m%d")
        base_time = available[-1]
    else:
        yesterday = now - timedelta(days=1)
        base_date = yesterday.strftime("%Y%m%d")
        base_time = "2300"

    return base_date, base_time


# =========================
# API 호출
# =========================
def fetch_weather():
    if not SERVICE_KEY:
        raise RuntimeError("KMA_SERVICE_KEY가 없습니다. GitHub Secrets를 확인하세요.")

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

    if res.status_code == 429:
        raise RuntimeError("기상청 API 요청 제한(429 Too Many Requests)")

    res.raise_for_status()

    data = res.json()

    try:
        items = data["response"]["body"]["items"]["item"]
    except Exception:
        raise RuntimeError(f"API 응답 형식이 예상과 다릅니다: {data}")

    if not items:
        raise RuntimeError("API 응답에 예보 데이터가 없습니다.")

    return items


# =========================
# 현재에 가장 가까운 예보 1세트 선택
# =========================
def choose_target_forecast(items):
    now = datetime.now(KST)
    now_key = now.strftime("%Y%m%d%H00")

    # fcstDate+fcstTime 후보 모으기
    forecast_keys = sorted({item["fcstDate"] + item["fcstTime"] for item in items})

    target_key = None
    for key in forecast_keys:
        if key >= now_key:
            target_key = key
            break

    if target_key is None:
        target_key = forecast_keys[0]

    values = {}
    for item in items:
        key = item["fcstDate"] + item["fcstTime"]
        if key == target_key:
            values[item["category"]] = item["fcstValue"]

    return values


# =========================
# 날씨 분류
# =========================
def classify_weather(values):
    tmp = str(values.get("TMP", "--"))
    sky = str(values.get("SKY", "1"))
    pty = str(values.get("PTY", "0"))

    # PTY 우선
    if pty == "1":
        icon_kind = "rainy"   # 비
    elif pty == "2":
        icon_kind = "snowy"   # 비/눈
    elif pty == "3":
        icon_kind = "snowy"   # 눈
    elif pty == "4":
        icon_kind = "rainy"   # 소나기
    else:
        if sky == "1":
            icon_kind = "sunny"
        elif sky == "3":
            icon_kind = "partly"
        elif sky == "4":
            icon_kind = "cloudy"
        else:
            icon_kind = "sunny"

    return icon_kind, tmp


# =========================
# 폰트 로드
# =========================
def load_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)

    # 폰트가 없을 때 fallback
    fallback_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in fallback_candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# =========================
# 가운데 정렬로 "서울 29" 쓰기
# =========================
def draw_location_temp(draw, area_name, temp, font, image_width, y):
    city_text = f"{area_name} "
    temp_text = f"{temp}"

    city_bbox = draw.textbbox((0, 0), city_text, font=font)
    temp_bbox = draw.textbbox((0, 0), temp_text, font=font)

    city_w = city_bbox[2] - city_bbox[0]
    temp_w = temp_bbox[2] - temp_bbox[0]
    total_w = city_w + temp_w

    start_x = (image_width - total_w) / 2

    draw.text((start_x, y), city_text, font=font, fill=CITY_COLOR)
    draw.text((start_x + city_w, y), temp_text, font=font, fill=TEMP_COLOR)


# =========================
# 이미지 합성
# =========================
def create_weather_image(icon_kind, temp):
    filename = IMAGE_MAP.get(icon_kind, "sunny.png")
    bg_path = os.path.join(ASSET_DIR, filename)

    if not os.path.exists(bg_path):
        raise RuntimeError(f"배경 이미지가 없습니다: {bg_path}")

    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = load_font(FONT_SIZE)

    draw_location_temp(draw, AREA_NAME, temp, font, img.width, TEXT_Y)

    img.save(OUTPUT_PATH)


# =========================
# 실패 시 기본 이미지 생성
# =========================
def create_fallback_image():
    bg_path = os.path.join(ASSET_DIR, "sunny.png")

    if not os.path.exists(bg_path):
        raise RuntimeError("fallback용 sunny.png도 없습니다.")

    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = load_font(FONT_SIZE)

    draw_location_temp(draw, AREA_NAME, "--", font, img.width, TEXT_Y)
    img.save(OUTPUT_PATH)


# =========================
# 메인
# =========================
def main():
    try:
        items = fetch_weather()
        values = choose_target_forecast(items)
        icon_kind, temp = classify_weather(values)
        create_weather_image(icon_kind, temp)
        print(f"완료: {icon_kind}, {AREA_NAME} {temp}")
    except Exception as e:
        print(f"[경고] 날씨 이미지 생성 중 오류: {e}")

        # 기존 weather.png가 있으면 유지
        if os.path.exists(OUTPUT_PATH):
            print("기존 weather.png를 유지합니다.")
            return

        # 기존 파일도 없으면 fallback 생성
        print("기존 weather.png가 없어 fallback 이미지를 생성합니다.")
        create_fallback_image()


if __name__ == "__main__":
    main()
