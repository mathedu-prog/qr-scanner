#!/usr/bin/env python3
"""產生 PWA 圖示：icon-192.png、icon-512.png、icon-maskable-512.png、apple-touch-icon.png
用法：python3 tools/make_icons.py
需求：pip install pillow
圖案：深色底 + 白色掃描框四角 + 強調色掃描線（與 App 內視覺一致）。
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SS = 4  # 超取樣倍率，讓邊緣更平滑

BG_TOP, BG_BOT = (22, 28, 44), (8, 10, 15)
ACCENT = (76, 141, 255)
WHITE = (255, 255, 255)


def gradient(size):
    """直向漸層底圖"""
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        c = tuple(int(BG_TOP[i] * (1 - t) + BG_BOT[i] * t) for i in range(3))
        for x in range(size):
            px[x, y] = c
    return img


def draw_mark(size, scale):
    """畫出圖案（透明底）。scale<1 會縮小圖案，用於 maskable 的安全區。"""
    S = size * SS
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    box = S * 0.50 * scale            # 掃描框邊長
    x0 = (S - box) / 2
    y0 = (S - box) / 2
    x1, y1 = x0 + box, y0 + box
    w = max(2, int(S * 0.052 * scale))   # 線寬
    arm = box * 0.34                  # 角線長度
    r = box * 0.16                    # 圓角

    def corner(cx, cy, sx, sy):
        # 以兩條直線 + 四分之一圓弧組成圓角線
        ax, ay = cx + sx * arm, cy
        bx, by = cx, cy + sy * arm
        d.line([(ax, ay), (cx + sx * r, cy)], fill=WHITE, width=w)
        d.line([(cx, cy + sy * r), (bx, by)], fill=WHITE, width=w)
        ccx, ccy = cx + sx * r, cy + sy * r      # 圓弧圓心
        rr = r + w / 2                           # PIL 的 arc 線寬往圓內長，外擴半個線寬才會與直線對齊
        bb = [ccx - rr, ccy - rr, ccx + rr, ccy + rr]
        start = {(1, 1): 180, (-1, 1): 270, (-1, -1): 0, (1, -1): 90}[(sx, sy)]
        d.arc(bb, start, start + 90, fill=WHITE, width=w)
        for px_, py_ in ((ax, ay), (bx, by)):      # 圓角端點
            d.ellipse([px_ - w / 2, py_ - w / 2, px_ + w / 2, py_ + w / 2], fill=WHITE)

    corner(x0, y0, 1, 1)
    corner(x1, y0, -1, 1)
    corner(x0, y1, 1, -1)
    corner(x1, y1, -1, -1)

    # 中央掃描線 + 光暈
    cy = S / 2
    lx0, lx1 = x0 + box * 0.14, x1 - box * 0.14
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line([(lx0, cy), (lx1, cy)], fill=ACCENT + (255,), width=int(w * 1.6))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.018 * scale))
    layer = Image.alpha_composite(layer, glow)
    d = ImageDraw.Draw(layer)
    d.line([(lx0, cy), (lx1, cy)], fill=ACCENT + (255,), width=int(w * 0.9))
    for px_ in (lx0, lx1):
        d.ellipse([px_ - w * 0.45, cy - w * 0.45, px_ + w * 0.45, cy + w * 0.45], fill=ACCENT + (255,))
    return layer


def make(size, scale=1.0, rounded=True, name="icon.png"):
    S = size * SS
    base = gradient(S).convert("RGBA")
    base = Image.alpha_composite(base, draw_mark(size, scale))
    if rounded:
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.225), fill=255)
        out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        out.paste(base, (0, 0), mask)
        base = out
    base = base.resize((size, size), Image.LANCZOS)
    if not rounded:
        base = base.convert("RGB")      # 不含透明度（maskable / apple-touch-icon）
    base.save(ROOT / name, optimize=True)
    print("✓", name, base.size)


if __name__ == "__main__":
    make(192, 1.0, True, "icon-192.png")
    make(512, 1.0, True, "icon-512.png")
    make(512, 0.78, False, "icon-maskable-512.png")   # 圖案縮小，確保落在 80% 安全區內
    make(180, 1.0, False, "apple-touch-icon.png")     # iOS 會自行套用圓角
