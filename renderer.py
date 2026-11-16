
import os
import subprocess
import qrcode
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920

NAVY = (12, 35, 70)
WHITE = (255, 255, 255)
LIGHT = (244, 247, 251)


def get_font_path(bold=False):
    family = "Noto Sans Arabic:style=Bold" if bold else "Noto Sans Arabic"
    return subprocess.check_output(
        ["fc-match", "-f", "%{file}", family],
        text=True
    ).strip()


REGULAR_FONT = get_font_path(False)
BOLD_FONT = get_font_path(True)


def load_font(size, bold=False):
    return ImageFont.truetype(
        BOLD_FONT if bold else REGULAR_FONT,
        size,
        layout_engine=ImageFont.Layout.RAQM
    )


def draw_centered(draw, text, y, font, color=NAVY):
    draw.text(
        (W // 2, y),
        str(text),
        font=font,
        fill=color,
        anchor="mm",
        direction="rtl",
        language="ar"
    )


def make_qr(url):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)

    return qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")


def make_scene(title, lines, number, total, qr_url=None):
    img = Image.new("RGB", (W, H), LIGHT)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 280), fill=NAVY)

    draw_centered(
        draw, "زبدة الوظائف", 115,
        load_font(58, True), WHITE
    )

    draw_centered(
        draw, "وظائف شاغرة", 205,
        load_font(35), WHITE
    )

    draw.rounded_rectangle(
        (65, 390, 1015, 1510),
        radius=45,
        fill=WHITE
    )

    draw_centered(
        draw, title, 510,
        load_font(54, True)
    )

    if qr_url:
        draw_centered(
            draw, "امسح الرمز للوصول إلى الوظيفة",
            680, load_font(38, True)
        )

        qr_img = make_qr(qr_url)
        qr_img = qr_img.resize(
            (440, 440),
            Image.Resampling.LANCZOS
        )

        img.paste(qr_img, (320, 800))

        draw_centered(
            draw, "افتح كاميرا جوالك وامسح الرمز",
            1340, load_font(34)
        )

    else:
        y = 720
        font = load_font(43)

        for line in lines:
            words = str(line).split()
            current = ""

            for word in words:
                test = (current + " " + word).strip()

                width = draw.textbbox(
                    (0, 0), test, font=font,
                    direction="rtl", language="ar"
                )[2]

                if width > 820 and current:
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
        draw, "التفاصيل وطريقة التقديم",
        1740, load_font(48, True), WHITE
    )

    draw_centered(
        draw, f"{number} / {total}",
        1850, load_font(30), WHITE
    )

    return img


def make_video_frames(data, output_dir="frames"):
    os.makedirs(output_dir, exist_ok=True)

    scenes = [
        ("وظيفة جديدة", ["فرصة وظيفية من زبدة الوظائف"])
    ]

    fields = [
        ("المسمى الوظيفي والجهة",
         [data.get("title", ""), data.get("company", "")]),

        ("مكان العمل", [data.get("city", "")]),

        ("تفاصيل الوظيفة",
         [data.get("target", ""), data.get("workType", "")]),

        ("المؤهلات والشروط",
         [data.get("qualification", "")])
    ]

    for heading, values in fields:
        values = [v for v in values if v]
        if values:
            scenes.append((heading, values, None))

    article_url = data.get(
        "article_url",
        "https://zubda-ksa.blogspot.com/"
    )

    scenes.append((
        "امسح الرمز الآن",
        [],
        article_url
    ))

    total = len(scenes)

    for i, scene in enumerate(scenes, start=1):
        heading, lines, *qr = scene
        qr_url = qr[0] if qr else None

        img = make_scene(
            heading, lines, i, total, qr_url
        )

        img.save(
            os.path.join(output_dir, f"frame_{i:03d}.png")
        )

    print(f"Created {total} video scenes.")


if __name__ == "__main__":
    make_video_frames({
        "title": "أخصائي موارد بشرية",
        "company": "شركة سعودية",
        "city": "الرياض",
        "target": "السعوديون",
        "workType": "دوام كامل",
        "qualification": "بكالوريوس",
        "article_url": "https://zubda-ksa.blogspot.com/"
    })
