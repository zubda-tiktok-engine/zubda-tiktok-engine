
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

W, H = 1080, 1920

NAVY = (12, 35, 70)
WHITE = (255, 255, 255)
GRAY = (225, 231, 239)
LIGHT = (244, 247, 251)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def arabic(text):
    text = str(text)
    return get_display(arabic_reshaper.reshape(text))


def load_font(size, bold=False):
    path = BOLD_PATH if bold else FONT_PATH
    return ImageFont.truetype(path, size)


def draw_centered(draw, text, y, font, color=NAVY):
    draw.text(
        (W // 2, y),
        arabic(text),
        font=font,
        fill=color,
        anchor="mm",
        direction="rtl"
    )


def make_scene(title, lines, number, total):
    img = Image.new("RGB", (W, H), LIGHT)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 280), fill=NAVY)
    draw_centered(draw, "زبدة الوظائف", 115, load_font(58, True), WHITE)
    draw_centered(draw, "وظائف شاغرة", 205, load_font(35), WHITE)

    draw.rounded_rectangle(
        (65, 390, 1015, 1510),
        radius=45,
        fill=WHITE
    )

    draw_centered(draw, title, 510, load_font(54, True))

    y = 720
    for line in lines:
        font = load_font(43)
        words = str(line).split()
        current = ""

        for word in words:
            test = (current + " " + word).strip()
            if draw.textbbox((0, 0), arabic(test), font=font)[2] > 820:
                if current:
                    draw_centered(draw, current, y, font)
                    y += 85
                current = word
            else:
                current = test

        if current:
            draw_centered(draw, current, y, font)
            y += 100

        y += 35

    draw.rectangle((0, 1640, W, H), fill=NAVY)
    draw_centered(
        draw,
        "التفاصيل وطريقة التقديم",
        1740,
        load_font(48, True),
        WHITE
    )
    draw_centered(
        draw,
        f"{number} / {total}",
        1850,
        load_font(30),
        WHITE
    )

    return img


def make_video_frames(data, output_dir="frames"):
    os.makedirs(output_dir, exist_ok=True)

    scenes = [
        ("وظيفة جديدة", ["فرصة وظيفية من زبدة الوظائف"])
    ]

    title = data.get("title", "")
    company = data.get("company", "")
    city = data.get("city", "")
    target = data.get("target", "")
    work_type = data.get("workType", "")
    qualification = data.get("qualification", "")

    if title or company:
        scenes.append(("المسمى الوظيفي والجهة",
                       [v for v in [title, company] if v]))

    if city:
        scenes.append(("مكان العمل", [city]))

    details = [v for v in [target, work_type] if v]
    if details:
        scenes.append(("تفاصيل الوظيفة", details))

    if qualification:
        scenes.append(("المؤهلات والشروط", [qualification]))

    scenes.append(("قدّم الآن", [
        "للتفاصيل وطريقة التقديم",
        "زر رابط المقال في الوصف"
    ]))

    total = len(scenes)

    for i, (heading, lines) in enumerate(scenes, start=1):
        img = make_scene(heading, lines, i, total)
        img.save(os.path.join(output_dir, f"frame_{i:03d}.png"))

    print(f"Created {total} video scenes.")


if __name__ == "__main__":
    make_video_frames({
        "title": "أخصائي موارد بشرية",
        "company": "مثال: شركة سعودية",
        "city": "الرياض",
        "target": "السعوديون",
        "workType": "دوام كامل",
        "qualification": "بكالوريوس"
    })
