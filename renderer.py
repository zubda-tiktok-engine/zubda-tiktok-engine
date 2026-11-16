
import os
import re
import shutil
import requests
import qrcode
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BLOG_URL = "https://zubda-ksa.blogspot.com/"
FEED_URL = BLOG_URL + "feeds/posts/default?alt=rss&max-results=1"

NAVY = (12, 35, 70)
WHITE = (255, 255, 255)
LIGHT = (244, 247, 251)


def get_font_path(bold=False):
    family = "Noto Sans Arabic:style=Bold" if bold else "Noto Sans Arabic"
    import subprocess
    return subprocess.check_output(
        ["fc-match", "-f", "%{file}", family],
        text=True
    ).strip()


REGULAR_FONT = get_font_path()
BOLD_FONT = get_font_path(True)


def font(size, bold=False):
    return ImageFont.truetype(
        BOLD_FONT if bold else REGULAR_FONT,
        size,
        layout_engine=ImageFont.Layout.RAQM
    )


def centered(draw, text, y, size=42, bold=False, color=NAVY):
    draw.text(
        (W // 2, y),
        str(text),
        font=font(size, bold),
        fill=color,
        anchor="mm",
        direction="rtl",
        language="ar"
    )


def wrap_text(text, max_width, size=42):
    result = []
    current = ""

    for word in str(text).split():
        test = (current + " " + word).strip()
        box = font(size).getbbox(test, direction="rtl")

        if box[2] - box[0] > max_width and current:
            result.append(current)
            current = word
        else:
            current = test

    if current:
        result.append(current)

    return result


def make_qr(url):
    qr = qrcode.QRCode(
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
    centered(draw, "زبدة الوظائف", 115, 58, True, WHITE)
    centered(draw, "وظائف شاغرة", 205, 35, False, WHITE)

    draw.rounded_rectangle(
        (65, 390, 1015, 1510),
        radius=45,
        fill=WHITE
    )

    centered(draw, title, 510, 52, True)

    if qr_url:
        centered(draw, "امسح الرمز للوصول إلى الوظيفة", 680, 38, True)

        qr_img = make_qr(qr_url).resize(
            (460, 460),
            Image.Resampling.LANCZOS
        )
        img.paste(qr_img, (310, 790))

        centered(draw, "استخدم كاميرا جوالك لمسح الرمز", 1335, 32)

    else:
        y = 720

        for line in lines:
            for part in wrap_text(line, 820, 43):
                centered(draw, part, y, 43)
                y += 85
            y += 25

    draw.rectangle((0, 1640, W, H), fill=NAVY)
    centered(draw, "التفاصيل وطريقة التقديم", 1740, 46, True, WHITE)
    centered(draw, f"{number} / {total}", 1850, 30, False, WHITE)

    return img


def get_latest_job():
    response = requests.get(
        FEED_URL,
        timeout=30,
        headers={"User-Agent": "ZubdaTikTokEngine/1.0"}
    )
    response.raise_for_status()

    feed = BeautifulSoup(response.content, "xml")
    item = feed.find("item")

    if not item:
        raise Exception("لم يتم العثور على وظيفة منشورة في خلاصة بلوجر")

    title = item.title.get_text(" ", strip=True)
    url = item.link.get_text(strip=True)

    content = item.find("content:encoded")
    if not content:
        content = item.description

    html = content.get_text() if content else ""
    soup = BeautifulSoup(html, "html.parser")

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all(["p", "li"])
    ]
    paragraphs = [p for p in paragraphs if p]

    full_text = "\n".join(paragraphs)

    parts = [p.strip() for p in title.split(" - ") if p.strip()]
    company = parts[-1] if len(parts) > 1 else ""
    job_title = " - ".join(parts[:-1]) if len(parts) > 1 else title

    def extract(pattern):
        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    city = extract(r"(?:الموقع|مكان العمل|المدينة)\s*:\s*([^\n،]+)")
    target = extract(r"(?:الفئة المستهدفة|الجنسية)\s*:\s*([^\n]+)")
    work_type = extract(r"(?:نوع العمل|طبيعة العمل)\s*:\s*([^\n]+)")
    qualification = extract(r"(?:المؤهل المطلوب|المؤهلات المطلوبة|المؤهل)\s*:\s*([^\n]+)")

    intro = ""
    for paragraph in paragraphs:
        if len(paragraph) > 25 and not re.search(
            r"^(الموقع|الخبرة المطلوبة|طريقة التقديم|للتقديم)",
            paragraph
        ):
            intro = paragraph
            break

    return {
        "title": job_title,
        "company": company,
        "city": city,
        "target": target,
        "work_type": work_type,
        "qualification": qualification,
        "intro": intro,
        "url": url
    }


def make_video_frames(job):
    if os.path.exists("frames"):
        shutil.rmtree("frames")

    os.makedirs("frames")

    scenes = [
        ("وظيفة جديدة", ["فرصة وظيفية من زبدة الوظائف"]),
        ("المسمى الوظيفي والجهة", [
            job["title"],
            job["company"]
        ])
    ]

    if job["intro"]:
        scenes.append(("نبذة عن الوظيفة", [job["intro"]]))

    if job["city"]:
        scenes.append(("مكان العمل", [job["city"]]))

    details = [
        job["target"],
        job["work_type"],
        job["qualification"]
    ]
    details = [x for x in details if x]

    if details:
        scenes.append(("تفاصيل الوظيفة", details))

    scenes.append(("امسح الرمز الآن", [], job["url"]))

    total = len(scenes)

    for i, scene in enumerate(scenes, start=1):
        heading, lines, *qr = scene
        qr_url = qr[0] if qr else None

        image = make_scene(
            heading, lines, i, total, qr_url
        )
        image.save(f"frames/frame_{i:03d}.png")

    description = [
        "💼 " + job["title"],
        "🏢 " + job["company"],
    ]

    if job["city"]:
        description.append("📍 مكان العمل: " + job["city"])

    if job["target"]:
        description.append("🎯 الفئة المستهدفة: " + job["target"])

    if job["work_type"]:
        description.append("⏰ نوع العمل: " + job["work_type"])

    if job["qualification"]:
        description.append("📘 المؤهلات: " + job["qualification"])

    description += [
        "",
        "🔗 رابط الوظيفة والتقديم:",
        job["url"],
        "",
        "💼 مدونة زبدة الوظائف:",
        BLOG_URL,
        "",
        "#وظائف #وظائف_السعودية"
    ]

    with open("description.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(description))

    print("تم إنشاء الفيديو والوصف للوظيفة:")
    print(job["title"])
    print(job["url"])


if __name__ == "__main__":
    job = get_latest_job()
    make_video_frames(job)
