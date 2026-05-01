"""Generate OG images + apple-touch-icon for the mirror demo.

Outputs:
  - og.png        (1200x630, landscape — primary OG for FB/X/LinkedIn)
  - og-square.png (1200x1200, square    — secondary for WhatsApp/iMessage)
  - apple-touch-icon.png (180x180, iOS bookmark)

Logo is rasterized from favicon.svg via headless Chrome (libcairo isn't
available on Windows ARM64 so cairosvg/svglib both fail). Always renders
the logo at 1024px and downscales via PIL Lanczos for crispness.

Run from the repo root: `python gen_og.py`
"""
import os
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

LOGO_SVG = "favicon.svg"
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"

BG = (10, 10, 12)
VIOLET = (139, 92, 246)
VIOLET_LIGHT = (167, 139, 250)
TEXT = (232, 232, 238)
TEXT_2 = (152, 152, 168)


def font(name, size):
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


def render_logo(size_px):
    """Rasterize favicon.svg to a transparent-bg PNG via headless Chrome."""
    SOURCE = 1024
    here = os.path.abspath(".").replace("\\", "/")
    with tempfile.TemporaryDirectory() as td:
        td_fwd = td.replace("\\", "/")
        html = (
            "<!doctype html><html><head><style>"
            "html,body{margin:0;padding:0;background:transparent;}"
            "body{display:flex;justify-content:center;align-items:center;"
            "width:100vw;height:100vh;}"
            "img{width:100vmin;height:100vmin;display:block;}"
            "</style></head><body>"
            f'<img src="file:///{here}/{LOGO_SVG}" alt="">'
            "</body></html>"
        )
        html_path = f"{td_fwd}/render.html"
        out_path = f"{td_fwd}/out.png"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_path}",
            f"--window-size={SOURCE},{SOURCE}",
            f"file:///{html_path}",
        ], check=True, capture_output=True)
        big = Image.open(out_path).convert("RGBA").copy()
    if size_px == SOURCE:
        return big
    return big.resize((size_px, size_px), Image.LANCZOS)


def build_canvas(W, H, *, brand_size, brand_y, head_size, head_lines,
                 head_y, line_h, chip_size, chip_h, chip_pad_x, chip_gap,
                 chips_y, url_size, url_y_from_bottom, max_row_w_pad):
    img = Image.new("RGB", (W, H), BG)

    # Top violet glow (radial, soft)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = W // 2, 40
    max_r = int(W * 0.85)
    for r in range(max_r, 0, -25):
        t = 1 - (r / max_r)
        a = int(55 * t * t)
        if a < 1:
            continue
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*VIOLET, a))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Brand row: logo + "Mirror"
    brand_text = "Mirror"
    brand_font = font("segoeuib.ttf", brand_size)
    b_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    b_w = b_bbox[2] - b_bbox[0]
    logo_size = int(brand_size * 1.4)
    gap = max(14, brand_size // 4)
    total_w = logo_size + gap + b_w
    start_x = (W - total_w) // 2

    logo_img = render_logo(logo_size)
    img_rgba = img.convert("RGBA")
    img_rgba.alpha_composite(logo_img, (start_x, brand_y))
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)
    text_offset_y = (logo_size - brand_size) // 2 + max(2, brand_size // 12)
    draw.text((start_x + logo_size + gap, brand_y + text_offset_y),
              brand_text, fill=TEXT, font=brand_font)

    # Headline
    head_font = font("segoeuib.ttf", head_size)
    for i, line in enumerate(head_lines):
        bbox = draw.textbbox((0, 0), line, font=head_font)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) // 2, head_y + i * line_h), line,
                  fill=TEXT, font=head_font)

    # Trait chips
    chips_font = font("segoeui.ttf", chip_size)
    chips = ["curated chaos", "analytical romantic",
             "weekend archivist", "tea over coffee"]
    widths = []
    for c in chips:
        bbox = draw.textbbox((0, 0), c, font=chips_font)
        widths.append((bbox[2] - bbox[0]) + chip_pad_x * 2)

    max_row_w = W - max_row_w_pad
    rows = [[]]
    row_w = 0
    for c, w in zip(chips, widths):
        next_w = row_w + w + (chip_gap if row_w else 0)
        if next_w > max_row_w and rows[-1]:
            rows.append([(c, w)])
            row_w = w
        else:
            rows[-1].append((c, w))
            row_w = next_w

    for ri, row in enumerate(rows):
        total = sum(w for _, w in row) + chip_gap * (len(row) - 1)
        cx_pos = (W - total) // 2
        cy_pos = chips_y + ri * (chip_h + 20)
        for label, w in row:
            draw.rounded_rectangle(
                [cx_pos, cy_pos, cx_pos + w, cy_pos + chip_h],
                radius=chip_h // 2,
                fill=(28, 22, 48), outline=(110, 80, 200), width=3,
            )
            draw.text((cx_pos + w // 2, cy_pos + chip_h // 2 - 2), label,
                      fill=VIOLET_LIGHT, font=chips_font, anchor="mm")
            cx_pos += w + chip_gap

    # URL at bottom
    url_font = font("consola.ttf", url_size)
    draw.text((W // 2, H - url_y_from_bottom), "mirror.psyrcuit.com",
              fill=TEXT_2, font=url_font, anchor="ma")

    return img


# ── og.png — 1200x630 landscape (primary social preview) ────────
landscape = build_canvas(
    W=1200, H=630,
    brand_size=44, brand_y=28,
    head_size=68, head_lines=["What does your desk/bookshelf",
                              "say about you?"],
    head_y=150, line_h=84,
    chip_size=26, chip_h=54, chip_pad_x=24, chip_gap=14,
    chips_y=420, url_size=30, url_y_from_bottom=46,
    max_row_w_pad=120,
)
landscape.save("og.png", "PNG", optimize=True)
print("og.png written — 1200x630 (landscape)")

# ── og-square.png — 1200x1200 (WhatsApp / iMessage / in-app) ────
square = build_canvas(
    W=1200, H=1200,
    brand_size=84, brand_y=110,
    head_size=96, head_lines=["What does your", "desk/bookshelf",
                              "say about you?"],
    head_y=290, line_h=110,
    chip_size=42, chip_h=84, chip_pad_x=38, chip_gap=18,
    chips_y=770, url_size=56, url_y_from_bottom=100,
    max_row_w_pad=200,
)
square.save("og-square.png", "PNG", optimize=True)
print("og-square.png written — 1200x1200 (square)")

# ── apple-touch-icon (180x180, dark bg + centered logo) ─────────
ATI = 180
ati = Image.new("RGB", (ATI, ATI), BG)
logo_ati = render_logo(int(ATI * 0.78))
ati_rgba = ati.convert("RGBA")
off = (ATI - logo_ati.width) // 2
ati_rgba.alpha_composite(logo_ati, (off, off))
ati_rgba.convert("RGB").save("apple-touch-icon.png", "PNG", optimize=True)
print(f"apple-touch-icon.png written — {ATI}x{ATI}")
