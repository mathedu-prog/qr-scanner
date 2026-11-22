#!/usr/bin/env python3
"""產生 PWA 圖示：icon-192.png、icon-512.png、icon-maskable-512.png、apple-touch-icon.png
用法：python3 tools/make_icons.py
需求：pip install pillow
圖案：深色底 + QR Code 縮圖（三個定位方塊 + 資料點）。
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
    """畫出 QR Code 縮圖樣式的圖案（透明底）：三個定位方塊 + 資料點，右下為強調色。
    scale<1 會縮小圖案，用於 maskable 的安全區。"""
    S = size * SS
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    box = S * 0.56 * scale            # 圖案邊長（9×9 格）
    u = box / 9
    x0 = (S - box) / 2
    y0 = (S - box) / 2

    def finder(cx, cy):
        # 定位方塊：外框 4u（線寬 0.9u）+ 中央實心方塊
        X, Y = x0 + cx * u, y0 + cy * u
        d.rounded_rectangle([X, Y, X + 4 * u, Y + 4 * u], radius=u * 0.9, outline=WHITE, width=int(u * 0.9))
        d.rounded_rectangle([X + 1.2 * u, Y + 1.2 * u, X + 2.8 * u, Y + 2.8 * u], radius=u * 0.35, fill=ACCENT + (255,))

    finder(0, 0); finder(5, 0); finder(0, 5)
    # 右下角資料點（模擬 QR 資料區）
    for cx, cy in [(5, 5), (7, 5), (6, 6), (8, 6), (5, 7), (7, 7), (6, 8), (8, 8), (8, 5)]:
        X, Y = x0 + cx * u, y0 + cy * u
        d.rounded_rectangle([X + u * 0.08, Y + u * 0.08, X + u * 0.92, Y + u * 0.92], radius=u * 0.25, fill=WHITE)
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
