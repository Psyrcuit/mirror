"""Generate og.png + apple-touch-icon.png using PIL + system fonts +
headless Chrome for the brand logo (libcairo isn't available on Windows
ARM64 so cairosvg/svglib both fail).

Run from the repo root: `python gen_og.py`
Outputs og.png (1200x1200) and apple-touch-icon.png (180x180).

Design priority: text must read at thumbnail size (~250px wide).
"""
import io, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

LOGO_SVG = "favicon.svg"
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"


def render_logo(size_px):
    """Rasterize favicon.svg to a transparent-bg PNG via headless Chrome.

    Chrome headless has a minimum window size and produces blank output
    below ~~~150px. Always render at 1024px then downscale via PIL Lanczos.
    """
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

W = H = 1200
BG = (10, 10, 12)
VIOLET = (139, 92, 246)
VIOLET_LIGHT = (167, 139, 250)
TEXT = (232, 232, 238)
TEXT_2 = (152, 152, 168)
TEXT_3 = (94, 94, 114)


def font(name, size):
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


img = Image.new("RGB", (W, H), BG)

# Top violet glow (radial)
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
cx, cy = W // 2, 60
for r in range(950, 0, -25):
    t = 1 - (r / 950)
    a = int(55 * t * t)
    if a < 1:
        continue
    gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*VIOLET, a))
glow = glow.filter(ImageFilter.GaussianBlur(80))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

draw = ImageDraw.Draw(img)

# ── BRAND ROW (top-centered) ─────────────────────────────
brand_text = "Mirror"
brand_font = font("segoeuib.ttf", 84)
b_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
b_w = b_bbox[2] - b_bbox[0]
logo_size = 120
gap = 28
total_w = logo_size + gap + b_w
start_x = (W - total_w) // 2
brand_y = 110

logo_img = render_logo(logo_size)
img_rgba = img.convert("RGBA")
img_rgba.alpha_composite(logo_img, (start_x, brand_y))
img = img_rgba.convert("RGB")
draw = ImageDraw.Draw(img)
draw.text((start_x + logo_size + gap, brand_y + 22), brand_text,
          fill=TEXT, font=brand_font)

# ── HEADLINE (massive, centered) ─────────────────────────
head_font = font("segoeuib.ttf", 96)
head_lines = ["What does your", "desk/bookshelf", "say about you?"]
head_y = 290
line_h = 110
for i, line in enumerate(head_lines):
    bbox = draw.textbbox((0, 0), line, font=head_font)
    lw = bbox[2] - bbox[0]
    draw.text(((W - lw) // 2, head_y + i * line_h), line,
              fill=TEXT, font=head_font)

# ── TRAIT CHIPS (big, centered, two-row) ─────────────────
chips_font = font("segoeui.ttf", 42)
chips = ["curated chaos", "analytical romantic",
         "weekend archivist", "tea over coffee"]
chip_color = (28, 22, 48)
chip_border = (110, 80, 200)
chip_pad_x = 38
chip_h = 84
chip_gap = 18

chips_y = 770

# Greedy two-row packing, each row centered
def measure(text):
    bbox = draw.textbbox((0, 0), text, font=chips_font)
    return (bbox[2] - bbox[0]) + chip_pad_x * 2

widths = [measure(c) for c in chips]
max_row_w = W - 200  # padding from edges

rows = [[]]
row_w = 0
for c, w in zip(chips, widths):
    if row_w + w + (chip_gap if row_w else 0) > max_row_w and rows[-1]:
        rows.append([])
        row_w = 0
    rows[-1].append((c, w))
    row_w += w + (chip_gap if row_w else 0)

for ri, row in enumerate(rows):
    total = sum(w for _, w in row) + chip_gap * (len(row) - 1)
    cx_pos = (W - total) // 2
    cy_pos = chips_y + ri * (chip_h + 20)
    for label, w in row:
        draw.rounded_rectangle(
            [cx_pos, cy_pos, cx_pos + w, cy_pos + chip_h],
            radius=chip_h // 2,
            fill=chip_color, outline=chip_border, width=3,
        )
        draw.text((cx_pos + w // 2, cy_pos + chip_h // 2 - 2), label,
                  fill=VIOLET_LIGHT, font=chips_font, anchor="mm")
        cx_pos += w + chip_gap

# ── BOTTOM URL (big, centered) ───────────────────────────
url_font = font("consola.ttf", 56)
draw.text((W // 2, H - 100), "mirror.psyrcuit.com",
          fill=TEXT_2, font=url_font, anchor="ma")

img.save("og.png", "PNG", optimize=True)
print(f"og.png written — {W}x{H}")

# ── apple-touch-icon (180x180, dark bg + centered logo) ──
ATI = 180
ati = Image.new("RGB", (ATI, ATI), BG)
logo_ati = render_logo(int(ATI * 0.78))
ati_rgba = ati.convert("RGBA")
off = (ATI - logo_ati.width) // 2
ati_rgba.alpha_composite(logo_ati, (off, off))
ati_rgba.convert("RGB").save("apple-touch-icon.png", "PNG", optimize=True)
print(f"apple-touch-icon.png written — {ATI}x{ATI}")
