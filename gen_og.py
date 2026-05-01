"""Generate og.png from scratch using PIL + Windows system fonts.

Run from the repo root: `python gen_og.py`
Outputs og.png (1200x1200) matching mirror.psyrcuit.com's brand.
Kept around so it's easy to regenerate after copy/style tweaks.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = H = 1200
BG = (10, 10, 12)
VIOLET = (139, 92, 246)
VIOLET_LIGHT = (167, 139, 250)
TEXT = (232, 232, 238)
TEXT_2 = (152, 152, 168)
TEXT_3 = (94, 94, 114)
BORDER = (34, 34, 42)
CARD_TOP = (20, 20, 26)
CARD_BOT = (14, 14, 20)


def font(name, size):
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


img = Image.new("RGB", (W, H), BG)

# Top violet glow (radial)
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
cx, cy = W // 2, 80
for r in range(900, 0, -25):
    t = 1 - (r / 900)
    a = int(45 * t * t)
    if a < 1:
        continue
    gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*VIOLET, a))
glow = glow.filter(ImageFilter.GaussianBlur(70))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

draw = ImageDraw.Draw(img)

# ── BRAND ROW ────────────────────────────────────────────
PAD = 100
draw.ellipse([PAD - 2, 130, PAD + 22, 154], fill=VIOLET)
# outer ring (subtle)
ring = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
ImageDraw.Draw(ring).ellipse([2, 2, 58, 58], outline=(*VIOLET, 80), width=2)
img.paste(ring, (PAD - 20, 112), ring)
draw.text((PAD + 50, 124), "Mirror", fill=TEXT, font=font("segoeuib.ttf", 38))

# ── TAGLINE ──────────────────────────────────────────────
draw.text((PAD, 240), "Personality identikit", fill=TEXT, font=font("segoeuib.ttf", 60))
draw.text((PAD, 312), "from your bookshelf.", fill=TEXT, font=font("segoeuib.ttf", 60))

# ── SUBTITLE ─────────────────────────────────────────────
sub = font("segoeui.ttf", 26)
draw.text((PAD, 410), "Upload an image of your desk or bookshelf —", fill=TEXT_2, font=sub)
draw.text((PAD, 446), "get a personalized identikit. Powered by Claude Opus 4.7.", fill=TEXT_2, font=sub)

# ── CARD ─────────────────────────────────────────────────
CX, CY, CW, CH = PAD, 540, 1000, 500

# Vertical gradient inside a rounded rect
card = Image.new("RGB", (CW, CH))
for y in range(CH):
    t = y / CH
    row = lerp(CARD_TOP, CARD_BOT, t)
    card.paste(row, (0, y, CW, y + 1))

mask = Image.new("L", (CW, CH), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, CW, CH], radius=24, fill=255)
img.paste(card, (CX, CY), mask)

# Border + accent line
draw.rounded_rectangle([CX, CY, CX + CW, CY + CH], radius=24, outline=BORDER, width=1)
draw.line([CX + 80, CY + 1, CX + CW - 80, CY + 1], fill=VIOLET, width=2)

# Card header
hx, hy = CX + 40, CY + 36
draw.ellipse([hx, hy + 8, hx + 12, hy + 20], fill=VIOLET)
draw.text((hx + 24, hy + 4), "Mirror reading", fill=TEXT, font=font("segoeuib.ttf", 22))
draw.text((CX + CW - 40, hy + 8), "#A4B2C0",
          fill=TEXT_3, font=font("consola.ttf", 14), anchor="ra")
draw.line([CX + 40, CY + 90, CX + CW - 40, CY + 90], fill=BORDER)

# Trait chips
trait_font = font("segoeui.ttf", 18)
chips = ["curated chaos", "analytical romantic", "weekend archivist", "tea over coffee"]
chip_x, chip_y = CX + 40, CY + 116
chip_color = (28, 22, 48)
chip_border = (88, 65, 165)
for label in chips:
    bbox = draw.textbbox((0, 0), label, font=trait_font)
    tw = bbox[2] - bbox[0]
    cw = tw + 36
    if chip_x + cw > CX + CW - 40:
        chip_x = CX + 40
        chip_y += 50
    draw.rounded_rectangle([chip_x, chip_y, chip_x + cw, chip_y + 40],
                           radius=20, fill=chip_color, outline=chip_border, width=1)
    draw.text((chip_x + cw // 2, chip_y + 11), label,
              fill=VIOLET_LIGHT, font=trait_font, anchor="ma")
    chip_x += cw + 12

# Synthesis (centered vertically in remaining space)
synth_font = font("segoeui.ttf", 22)
synth_lines = [
    "Books shelved by mood not Dewey, three notebooks",
    "in active use, the careful kind of disorder",
    "that means somebody actually thinks here.",
]
sy = CY + 240
for i, line in enumerate(synth_lines):
    draw.text((CX + 40, sy + i * 36), line, fill=TEXT, font=synth_font)

# Vibe block
draw.line([CX + 40, CY + 380, CX + CW - 40, CY + 380], fill=BORDER)
draw.text((CX + 40, CY + 400), "VIBE", fill=TEXT_3,
          font=font("consolab.ttf", 12))
draw.text((CX + 100, CY + 396), "thoughtful clutter; quiet joy",
          fill=VIOLET_LIGHT, font=font("segoeuii.ttf", 20))

# Footer
draw.line([CX + 40, CY + 450, CX + CW - 40, CY + 450], fill=BORDER)
draw.text((CX + 40, CY + 468), "mirror.psyrcuit.com",
          fill=TEXT_3, font=font("consola.ttf", 14))
draw.text((CX + CW - 40, CY + 468), "#mirror",
          fill=TEXT_3, font=font("consola.ttf", 14), anchor="ra")

# Bottom URL
draw.text((W // 2, H - 70), "mirror.psyrcuit.com",
          fill=TEXT_2, font=font("consola.ttf", 24), anchor="ma")

img.save("og.png", "PNG", optimize=True)
print(f"og.png written — {W}x{H}")
