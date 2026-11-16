import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
NAVY = (12, 35, 70)
WHITE = (255, 255, 255)
GRAY = (225, 231, 239)

def make_video_image(data, output="frame.png"):
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 260), fill=NAVY)
    draw.text((W//2, 105), "زبدة الوظائف",
              fill=WHITE, anchor="mm")

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = ImageFont.truetype(font_path, 48)

    title = data.get("title", "وظيفة جديدة")
    company = data.get("company", "")

    draw.text((W//2, 430), "💼 وظيفة جديدة",
              fill=NAVY, anchor="mm")

    y = 600
    for value in [title, company, data.get("city", ""),
                  data.get("target", ""),
                  data.get("workType", ""),
                  data.get("qualification", "")]:
        if value:
            for line in textwrap.wrap(value, width=27):
                draw.text((W//2, y), line, font=font,
                          fill=NAVY, anchor="mm")
                y += 85
            y += 35

    draw.rectangle((0, 1660, W, H), fill=NAVY)
    draw.text((W//2, 1760), "التفاصيل وطريقة التقديم",
              fill=WHITE, font=font, anchor="mm")

    img.save(output)

if __name__ == "__main__":
    make_video_image({
        "title": "مثال: أخصائي موارد بشرية",
        "company": "اسم الجهة",
        "city": "الرياض"
    })
