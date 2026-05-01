"""Generate og.png from scratch using PIL + Windows system fonts.

Run from the repo root: `python gen_og.py`
Outputs og.png (1200x1200) matching mirror.psyrcuit.com's brand.

Design priority: text must read at thumbnail size (~250px wide). That means
short copy, very large fonts, no detail-card mockup.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
brand_font = font("segoeuib.ttf", 56)
b_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
b_w = b_bbox[2] - b_bbox[0]
b_h = b_bbox[3] - b_bbox[1]
dot_size = 36
gap = 24
total_w = dot_size + gap + b_w
start_x = (W - total_w) // 2
brand_y = 130

# Outer ring
ring = Image.new("RGBA", (dot_size + 24, dot_size + 24), (0, 0, 0, 0))
ImageDraw.Draw(ring).ellipse(
    [2, 2, dot_size + 22, dot_size + 22],
    outline=(*VIOLET, 90), width=2
)
img.paste(ring, (start_x - 12, brand_y - 12 + 12), ring)
# Solid violet dot
draw.ellipse(
    [start_x, brand_y + 12, start_x + dot_size, brand_y + 12 + dot_size],
    fill=VIOLET,
)
# Wordmark
draw.text((start_x + dot_size + gap, brand_y), brand_text,
          fill=TEXT, font=brand_font)

# ── HEADLINE (massive, centered, 3 lines) ────────────────
head_font = font("segoeuib.ttf", 124)
head_lines = ["What your", "bookshelf", "says about you."]
head_y = 280
line_h = 132
for i, line in enumerate(head_lines):
    bbox = draw.textbbox((0, 0), line, font=head_font)
    lw = bbox[2] - bbox[0]
    draw.text(((W - lw) // 2, head_y + i * line_h), line,
              fill=TEXT, font=head_font)

# ── TRAIT CHIPS (big, centered, two-row) ─────────────────
chips_font = font("segoeui.ttf", 32)
chips = ["curated chaos", "analytical romantic",
         "weekend archivist", "tea over coffee"]
chip_color = (28, 22, 48)
chip_border = (110, 80, 200)
chip_pad_x = 32
chip_h = 64
chip_gap = 16

chips_y = 800

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
    cy_pos = chips_y + ri * (chip_h + 16)
    for label, w in row:
        draw.rounded_rectangle(
            [cx_pos, cy_pos, cx_pos + w, cy_pos + chip_h],
            radius=chip_h // 2,
            fill=chip_color, outline=chip_border, width=2,
        )
        draw.text((cx_pos + w // 2, cy_pos + chip_h // 2 - 2), label,
                  fill=VIOLET_LIGHT, font=chips_font, anchor="mm")
        cx_pos += w + chip_gap

# ── BOTTOM URL (big, centered) ───────────────────────────
url_font = font("consola.ttf", 38)
draw.text((W // 2, H - 90), "mirror.psyrcuit.com",
          fill=TEXT_2, font=url_font, anchor="ma")

img.save("og.png", "PNG", optimize=True)
print(f"og.png written — {W}x{H}")
