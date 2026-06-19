import os
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

# =========================
# 기본 설정
# =========================
ASSET_DIR = "assets"
FONT_PATH = os.path.join(ASSET_DIR, "fonts", "handwriting.ttf")
OUTPUT_PATH = "date.png"

# 최종 위젯 크기
WIDGET_WIDTH = 171
WIDGET_HEIGHT = 279

# 날짜 글씨 설정
FONT_SIZE = 23
TEXT_Y = 70

KST = timezone(timedelta(hours=9))

# 시간대별 배경 이미지
BACKGROUND_MAP = {
    "dawn": "date_dawn.png",
    "morning": "date_morning.png",
    "afternoon": "date_afternoon.png",
    "night": "date_night.png",
}

# 시간대별 글씨 색상
TEXT_COLOR_MAP = {
    "dawn": "#5c5243",       # 새벽: 밝은 배경용 진한 회갈색
    "morning": "#4f4535",    # 아침: 기존 진한 갈색
    "afternoon": "#4f4535",  # 오후: 기존 진한 갈색
    "night": "#f4edcf",      # 밤: 어두운 배경용 밝은 아이보리
}

# 시간대별 외곽선 설정
# None이면 외곽선 없음
TEXT_STROKE_MAP = {
    "dawn": {
        "stroke_fill": None,
        "stroke_width": 0,
    },
    "morning": {
        "stroke_fill": None,
        "stroke_width": 0,
    },
    "afternoon": {
        "stroke_fill": None,
        "stroke_width": 0,
    },
    "night": {
        "stroke_fill": "#2c315f",  # 밤 배경과 어울리는 남보라색 외곽선
        "stroke_width": 1,
    },
}


# =========================
# 시간대 분류
# =========================
def get_time_period(now):
    hour = now.hour

    if 0 <= hour < 6:
        return "dawn"
    elif 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "night"


# =========================
# 요일 한글 변환
# =========================
def get_korean_weekday(now):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return weekdays[now.weekday()]


# =========================
# 폰트 로드
# =========================
def load_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)

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
# 가운데 정렬 텍스트
# =========================
def draw_center_text(
    draw,
    text,
    y,
    font,
    fill,
    image_width,
    stroke_fill=None,
    stroke_width=0,
):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (image_width - text_width) / 2

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=stroke_width,
    )


# =========================
# 날짜 이미지 생성
# =========================
def create_date_image():
    now = datetime.now(KST)

    period = get_time_period(now)
    bg_filename = BACKGROUND_MAP[period]
    bg_path = os.path.join(ASSET_DIR, bg_filename)

    if not os.path.exists(bg_path):
        raise RuntimeError(f"배경 이미지가 없습니다: {bg_path}")

    img = Image.open(bg_path).convert("RGBA")

    # 혹시 원본 크기가 다르면 171x279로 맞춤
    if img.size != (WIDGET_WIDTH, WIDGET_HEIGHT):
        img = img.resize((WIDGET_WIDTH, WIDGET_HEIGHT), Image.LANCZOS)

    draw = ImageDraw.Draw(img)
    font = load_font(FONT_SIZE)

    weekday = get_korean_weekday(now)
    date_text = f"{now.year}.{now.month:02d}.{now.day:02d} {weekday}"

    text_color = TEXT_COLOR_MAP[period]
    stroke_config = TEXT_STROKE_MAP[period]

    draw_center_text(
        draw=draw,
        text=date_text,
        y=TEXT_Y,
        font=font,
        fill=text_color,
        image_width=img.width,
        stroke_fill=stroke_config["stroke_fill"],
        stroke_width=stroke_config["stroke_width"],
    )

    img.save(OUTPUT_PATH)

    print(f"완료: {OUTPUT_PATH} / {period} / {date_text}")


# =========================
# 메인
# =========================
def main():
    create_date_image()


if __name__ == "__main__":
    main()
