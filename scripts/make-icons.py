#!/usr/bin/env python3
"""Generates original Android launcher icons + splash screens (anvil-and-flame | snow-crystal emblem)."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

RES = Path(__file__).resolve().parent.parent / "android/app/src/main/res"
BG = (11, 13, 18, 255)
BRONZE = (205, 140, 62, 255)
BRONZE_D = (130, 80, 30, 255)
FLAME = (255, 170, 60, 255)
FLAME_H = (255, 235, 150, 255)
ICE = (150, 215, 255, 255)
ICE_D = (70, 130, 190, 255)
S = 1024  # supersampled canvas


def emblem(size=S):
    """Emblem on transparent canvas, designed inside the central ~66% safe zone."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S // 2, S // 2
    r = 300
    # Disc rim
    d.ellipse([cx - r - 18, cy - r - 18, cx + r + 18, cy + r + 18], fill=(60, 60, 70, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(18, 21, 29, 255))

    # Left half: anvil + flame (clipped to left)
    left = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(left)
    # anvil: horn, face, waist, base
    ld.polygon([(cx - 270, cy + 20), (cx - 150, cy - 10), (cx + 40, cy - 10), (cx + 40, cy + 50), (cx - 140, cy + 50)], fill=BRONZE)
    ld.polygon([(cx - 150, cy - 10), (cx + 40, cy - 10), (cx + 40, cy + 15), (cx - 150, cy + 15)], fill=(235, 175, 90, 255))
    ld.polygon([(cx - 90, cy + 50), (cx + 40, cy + 50), (cx + 40, cy + 150), (cx - 40, cy + 150)], fill=BRONZE_D)
    ld.rectangle([cx - 140, cy + 150, cx + 40, cy + 200], fill=BRONZE)
    # flame above the anvil
    ld.polygon([(cx - 110, cy - 20), (cx - 150, cy - 110), (cx - 100, cy - 170), (cx - 105, cy - 240),
                (cx - 40, cy - 160), (cx - 10, cy - 215), (cx + 10, cy - 100), (cx - 20, cy - 20)], fill=FLAME)
    ld.polygon([(cx - 90, cy - 20), (cx - 100, cy - 80), (cx - 60, cy - 130), (cx - 40, cy - 80), (cx - 30, cy - 20)], fill=FLAME_H)
    # Right half: snow crystal
    right = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(right)
    ccx, ccy = cx + 8, cy
    for k in range(6):
        a = math.radians(k * 60 - 90)
        ex, ey = ccx + 230 * math.cos(a), ccy + 230 * math.sin(a)
        rd.line([(ccx, ccy), (ex, ey)], fill=ICE, width=22)
        for t, ln in ((0.55, 85), (0.8, 55)):
            bx, by = ccx + 230 * t * math.cos(a), ccy + 230 * t * math.sin(a)
            for sgn in (-1, 1):
                b = a + sgn * math.radians(50)
                rd.line([(bx, by), (bx + ln * math.cos(b), by + ln * math.sin(b))], fill=ICE, width=14)
    rd.regular_polygon((ccx, ccy, 42), 6, rotation=0, fill=(230, 247, 255, 255))
    # Clip halves with a diagonal split
    for layer, is_left in ((left, True), (right, False)):
        mask = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(mask)
        if is_left:
            md.polygon([(0, 0), (cx + 20, 0), (cx - 20, S), (0, S)], fill=255)
        else:
            md.polygon([(cx + 20, 0), (S, 0), (S, S), (cx - 20, S)], fill=255)
        disc = Image.new("L", (S, S), 0)
        ImageDraw.Draw(disc).ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], fill=255)
        mask = Image.composite(mask, Image.new("L", (S, S), 0), disc)
        layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", (S, S), 0), mask))
        img.alpha_composite(layer)
    # Split seam
    d = ImageDraw.Draw(img)
    d.line([(cx + 20, cy - r + 10), (cx - 20, cy + r - 10)], fill=(240, 220, 170, 255), width=8)
    glow = img.filter(ImageFilter.GaussianBlur(14))
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(img)
    return out


def save(img, path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((size, size), Image.LANCZOS).save(path)


def main():
    em = emblem()
    full = Image.new("RGBA", (S, S), BG)
    full.alpha_composite(em.resize((S, S)))
    # Legacy icon uses a tighter crop of the emblem so it fills the tile.
    tight = em.crop((150, 150, S - 150, S - 150)).resize((S, S), Image.LANCZOS)
    legacy = Image.new("RGBA", (S, S), BG)
    legacy.alpha_composite(tight)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=S // 5, fill=255)
    legacy_sq = Image.new("RGBA", (S, S), (0, 0, 0, 0)); legacy_sq.paste(legacy, mask=mask)
    circ = Image.new("L", (S, S), 0); ImageDraw.Draw(circ).ellipse([0, 0, S - 1, S - 1], fill=255)
    legacy_rd = Image.new("RGBA", (S, S), (0, 0, 0, 0)); legacy_rd.paste(legacy, mask=circ)

    for dens, px, fg in (("mdpi", 48, 108), ("hdpi", 72, 162), ("xhdpi", 96, 216), ("xxhdpi", 144, 324), ("xxxhdpi", 192, 432)):
        save(legacy_sq, RES / f"mipmap-{dens}/ic_launcher.png", px)
        save(legacy_rd, RES / f"mipmap-{dens}/ic_launcher_round.png", px)
        save(em, RES / f"mipmap-{dens}/ic_launcher_foreground.png", fg)  # adaptive layer, transparent

    (RES / "values/ic_launcher_background.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#0B0D12</color>\n</resources>\n')

    # Splash: near-black with centred emblem + title rule
    def splash(w, h):
        im = Image.new("RGBA", (w, h), BG)
        s = int(min(w, h) * 0.5)
        im.alpha_composite(em.resize((s, s), Image.LANCZOS), ((w - s) // 2, (h - s) // 2))
        return im.convert("RGB")

    sizes = {"mdpi": (320, 480), "hdpi": (480, 800), "xhdpi": (720, 1280), "xxhdpi": (960, 1600), "xxxhdpi": (1280, 1920)}
    for dens, (w, h) in sizes.items():
        splash(w, h).save(RES / f"drawable-port-{dens}/splash.png")
        splash(h, w).save(RES / f"drawable-land-{dens}/splash.png")
    splash(480, 320).save(RES / "drawable/splash.png")
    print("icons + splash written to", RES)


if __name__ == "__main__":
    main()
