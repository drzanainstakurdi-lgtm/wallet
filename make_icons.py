# Regenerates the app icons:  python make_icons.py   (needs: pip install pillow)
from PIL import Image, ImageDraw, ImageFilter
S = 1024

def make(maskable=False):
    import numpy as np
    t = (np.add.outer(np.arange(S), np.arange(S)) / (2 * S - 2))[..., None]
    c1, c2 = np.array((226, 138, 106)), np.array((196, 96, 62))
    base = Image.fromarray((c1 + (c2 - c1) * t).astype("uint8"), "RGB").convert("RGBA")
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((560, -160, 1160, 440), fill=(255, 214, 190, 150))
    base = Image.alpha_composite(base, glow.filter(ImageFilter.GaussianBlur(110)))
    k = 0.66 if maskable else 1.0
    P = lambda x, y: (512 + (x - 512) * k, 512 + (y - 512) * k)
    def rr(d, box, r, fill):
        (x0, y0), (x1, y1) = P(box[0], box[1]), P(box[2], box[3])
        d.rounded_rectangle((x0, y0, x1, y1), radius=r * k, fill=fill)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rr(ImageDraw.Draw(shadow), (180, 400, 844, 820), 110, (0, 0, 0, 110))
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(28)))
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    rr(d, (240, 240, 780, 430), 64, (255, 255, 255, 120))       # card peeking out
    rr(d, (180, 350, 844, 780), 110, (255, 255, 255, 246))      # wallet body
    rr(d, (560, 500, 890, 650), 75, (31, 30, 29, 255))        # clasp
    cx, cy = P(655, 575); r = 34 * k
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255))
    return Image.alpha_composite(base, g)

main, mask = make(False), make(True)
out = "static/icons/"
main.resize((180, 180), Image.LANCZOS).convert("RGB").save(out + "apple-touch-icon.png")
main.resize((192, 192), Image.LANCZOS).convert("RGB").save(out + "icon-192.png")
main.resize((512, 512), Image.LANCZOS).convert("RGB").save(out + "icon-512.png")
mask.resize((512, 512), Image.LANCZOS).convert("RGB").save(out + "icon-maskable-512.png")
main.resize((32, 32), Image.LANCZOS).convert("RGB").save(out + "favicon-32.png")
print("ok")
