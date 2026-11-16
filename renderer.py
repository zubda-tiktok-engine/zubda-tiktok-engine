
import os
import re
import json
import subprocess
import requests
import qrcode

from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


W = 1080
BLOG_URL = "https://zubda-ksa.blogspot.com/"
FEED_URL = BLOG_URL + "feeds/posts/default?alt=rss&max-results=20"
PROCESSED_FILE = "images_processed.json"
OUTPUT_DIR = "images"

PALETTES = [
    ((12, 35, 70), (255, 255, 255), (235, 242, 250), (35, 115, 190)),
    ((25, 75, 65), (255, 255, 255), (235, 247, 240), (55, 145, 105)),
    ((75, 42, 100), (255, 255, 255), (247, 239, 252), (145, 85, 180)),
    ((130, 55, 35), (255, 255, 255), (255, 243, 235), (215, 115, 65)),
    ((35, 55, 90), (255, 255, 255), (238, 244, 255), (80, 120, 200)),
    ((65, 75, 35), (255, 255, 255), (246, 248, 232), (140, 155, 65)),
    ((100, 45, 60), (255, 255, 255), (252, 239, 244), (190, 85, 115)),
    ((30, 75, 100), (255, 255, 255), (235, 247, 252), (55, 150, 185)),
    ((75, 65, 45), (255, 255, 255), (250, 246, 235), (170, 135, 65)),
    ((35, 45, 55), (255, 255, 255), (240, 244, 247), (100, 130, 155)),
]

LAYOUTS = [
    "classic", "sidebar", "circle", "split", "outline",
    "ribbon", "vertical", "double", "pill", "geometric"
]


def get_font_path(bold=False):
    family = "Noto Sans Arabic:style=Bold" if bold else "Noto Sans Arabic"
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


def normalize_url(url):
    if not url:
        return ""

    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()

    if not host:
        return url.strip().rstrip("/")

    port = parts.port
    if port and not (
        (scheme == "https" and port == 443)
        or (scheme == "http" and port == 80)
    ):
        host = f"{host}:{port}"

    path = parts.path.rstrip("/") or "/"

    return urlunsplit((scheme, host, path, "", ""))


def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return []

    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, list) else []


def save_processed(urls):
    unique = {}

    for url in urls:
        key = normalize_url(url)
        if key:
            unique[key] = url

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(
            sorted(unique.values()),
            f,
            ensure_ascii=False,
            indent=2
        )


def wrap_text(text, max_width, size, bold=False):
    result = []
    current = ""

    for word in str(text).split():
        test = (current + " " + word).strip()
        box = font(size, bold).getbbox(
            test,
            direction="rtl",
            language="ar"
        )

        if box[2] - box[0] > max_width and current:
            result.append(current)
            current = word
        else:
            current = test

    if current:
        result.append(current)

    return result


def get_paragraphs(item):
    content = item.find("content:encoded")
    if not content:
        content = item.find("description")

    html = content.get_text() if content else ""
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "iframe"]):
        element.decompose()

    paragraphs = []

    for element in soup.find_all(["p", "li", "h2", "h3"]):
        text = element.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        if text and text not in paragraphs:
            paragraphs.append(text)

    if not paragraphs:
        text = soup.get_text("\n", strip=True)
        paragraphs = [
            re.sub(r"\s+", " ", p).strip()
            for p in text.splitlines()
            if p.strip()
        ]

    return paragraphs


def extract_job(item):
    title = item.title.get_text(" ", strip=True)
    url = item.link.get_text(strip=True)

    paragraphs = get_paragraphs(item)

    parts = [p.strip() for p in title.split(" - ") if p.strip()]

    company = parts[-1] if len(parts) > 1 else ""
    job_title = " - ".join(parts[:-1]) if len(parts) > 1 else title

    full_text = "\n".join(paragraphs)

    def extract(pattern):
        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    city = extract(
        r"(?:الموقع|مكان العمل|المدينة)\s*:\s*([^\n،]+)"
    )
    target = extract(
        r"(?:الفئة المستهدفة|الجنسية)\s*:\s*([^\n]+)"
    )
    work_type = extract(
        r"(?:نوع العمل|طبيعة العمل)\s*:\s*([^\n]+)"
    )
    qualification = extract(
        r"(?:المؤهل المطلوب|المؤهلات المطلوبة|المؤهل)\s*:\s*([^\n]+)"
    )

    return {
        "title": job_title,
        "company": company,
        "city": city,
        "target": target,
        "work_type": work_type,
        "qualification": qualification,
        "paragraphs": paragraphs,
        "url": url
    }


def draw_center(draw, text, y, size, color, bold=False):
    draw.text(
        (W // 2, y),
        str(text),
        font=font(size, bold),
        fill=color,
        anchor="mm",
        direction="rtl",
        language="ar"
    )


def draw_layout(draw, height, design, primary, white, light, accent):
    layout = LAYOUTS[(design - 1) % 10]

    draw.rectangle((0, 0, W, height), fill=light)

    if layout == "classic":
        draw.rectangle((0, 0, W, 300), fill=primary)

    elif layout == "sidebar":
        draw.rectangle((0, 0, 35, height), fill=accent)
        draw.rectangle((35, 0, W, 270), fill=primary)

    elif layout == "circle":
        draw.rectangle((0, 0, W, 290), fill=primary)
        draw.ellipse((780, -160, 1200, 260), fill=accent)

    elif layout == "split":
        draw.rectangle((0, 0, W, 180), fill=primary)
        draw.rectangle((0, 180, W, 280), fill=accent)

    elif layout == "outline":
        draw.rectangle((0, 0, W, 260), fill=light)
        draw.rounded_rectangle(
            (35, 35, 1045, 245),
            radius=35,
            outline=primary,
            width=9
        )

    elif layout == "ribbon":
        draw.rectangle((0, 0, W, 280), fill=primary)
        draw.polygon(
            [(0, 250), (W, 250), (W - 100, 340), (100, 340)],
            fill=accent
        )

    elif layout == "vertical":
        draw.rectangle((0, 0, W, height), fill=light)
        draw.rectangle((0, 0, W, 230), fill=primary)
        draw.rectangle((0, 230, 22, height), fill=accent)

    elif layout == "double":
        draw.rectangle((0, 0, W, 280), fill=primary)
        draw.rectangle((0, 260, W, 285), fill=accent)

    elif layout == "pill":
        draw.rectangle((0, 0, W, 300), fill=light)
        draw.rounded_rectangle(
            (65, 45, 1015, 260),
            radius=100,
            fill=primary
        )

    elif layout == "geometric":
        draw.rectangle((0, 0, W, 280), fill=primary)
        draw.polygon(
            [(0, 0), (260, 0), (0, 260)],
            fill=accent
        )
        draw.polygon(
            [(W, 0), (W - 250, 0), (W, 250)],
            fill=accent
        )

    return layout


def create_qr(url):
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


def render_job(job, index, design):
    primary, white, light, accent = PALETTES[
        (design - 1) // 10
    ]

    sections = []

    if job["paragraphs"]:
        sections.append(("تفاصيل الإعلان", job["paragraphs"]))

    metadata = []

    if job["city"]:
        metadata.append("📍 مكان العمل: " + job["city"])

    if job["target"]:
        metadata.append("🎯 الفئة المستهدفة: " + job["target"])

    if job["work_type"]:
        metadata.append("⏰ نوع العمل: " + job["work_type"])

    if job["qualification"]:
        metadata.append("📘 المؤهلات: " + job["qualification"])

    if metadata:
        sections.append(("معلومات الوظيفة", metadata))

    prepared = []
    total_lines = 0

    for heading, paragraphs in sections:
        prepared.append((heading, paragraphs))

        for paragraph in paragraphs:
            total_lines += len(wrap_text(paragraph, 850, 34)) + 1

    height = max(1900, 1550 + total_lines * 53)

    img = Image.new("RGB", (W, height), light)
    draw = ImageDraw.Draw(img)

    draw_layout(
        draw, height, design,
        primary, white, light, accent
    )

    draw_center(draw, "زبدة الوظائف", 85, 54, white, True)
    draw_center(draw, "وظائف شاغرة", 165, 34, white)

    draw_center(
        draw,
        job["title"],
        390,
        53,
        primary,
        True
    )

    if job["company"]:
        draw_center(
            draw,
            "الجهة: " + job["company"],
            475,
            37,
            accent,
            True
        )

    content_top = 570
    content_bottom = height - 570

    draw.rounded_rectangle(
        (55, content_top, 1025, content_bottom),
        radius=35,
        fill=white,
        outline=accent,
        width=4
    )

    y = content_top + 65

    for heading, paragraphs in prepared:
        draw_center(draw, heading, y, 42, primary, True)
        y += 85

        for paragraph in paragraphs:
            lines = wrap_text(paragraph, 850, 34)

            for line in lines:
                draw_center(draw, line, y, 34, primary)
                y += 53

            y += 18

        y += 20

    qr = create_qr(job["url"])
    qr = qr.resize((350, 350), Image.Resampling.LANCZOS)

    qr_y = height - 490

    draw_center(
        draw,
        "امسح الرمز للوصول إلى الوظيفة",
        qr_y - 55,
        35,
        primary,
        True
    )

    img.paste(qr, ((W - 350) // 2, qr_y))

    footer_y = height - 80

    draw_center(
        draw,
        f"زبدة الوظائف  |  التصميم {design} من 100",
        footer_y,
        27,
        accent,
        True
    )

    folder = os.path.join(OUTPUT_DIR, str(index))
    os.makedirs(folder, exist_ok=True)

    image_path = os.path.join(folder, "post.png")
    img.save(image_path, optimize=True)

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

    with open(
        os.path.join(folder, "description.txt"),
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(description))

    print(
        f"تم إنشاء صورة الوظيفة: {job['title']} "
        f"| التصميم {design}/100"
    )


def main():
    response = requests.get(
        FEED_URL,
        timeout=30,
        headers={"User-Agent": "ZubdaTikTokEngine/2.0"}
    )
    response.raise_for_status()

    feed = BeautifulSoup(response.content, "xml")
    items = feed.find_all("item")

    processed = load_processed()

    seen_urls = {
        normalize_url(url)
        for url in processed
        if normalize_url(url)
    }

    new_items = []

    for item in items:
        if not item.link:
            continue

        url = item.link.get_text(strip=True)
        normalized = normalize_url(url)

        if not normalized:
            continue

        if normalized in seen_urls:
            print("تجاوز رابط مكرر أو سبق إنتاجه:", url)
            continue

        seen_urls.add(normalized)
        new_items.append(item)

    if not new_items:
        print("لا توجد وظائف جديدة.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    starting_count = len(seen_urls)

    for index, item in enumerate(new_items, start=1):
        url = item.link.get_text(strip=True)

        design = ((starting_count + index - 1) % 100) + 1

        try:
            job = extract_job(item)

            render_job(job, index, design)

            processed.append(url)
            save_processed(processed)

        except Exception as error:
            print("تعذر إنشاء صورة الوظيفة:", url)
            print("السبب:", error)

    print("انتهى إنشاء صور الوظائف الجديدة.")


if __name__ == "__main__":
    main()
