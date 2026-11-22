#!/usr/bin/env python3
"""產生「安裝教學頁」QR Code：qr-tutorial.png（內容為 install.html 的網址），並以 OpenCV 解碼驗證。
用法：python3 tools/make_tutorial_qr.py <GitHub帳號> <repo名稱>"""
import sys
from pathlib import Path
import cv2, numpy as np, qrcode
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
url = f"https://{sys.argv[1]}.github.io/{sys.argv[2]}/install.html"
qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0, box_size=1)
qr.add_data(url); qr.make(fit=True)
m, q, sc = qr.get_matrix(), 4, 16          # 安靜區 4 模組、每模組 16 像素
n = (len(m) + q * 2) * sc
arr = np.full((n, n), 255, np.uint8)
for y, row in enumerate(m):
    for x, v in enumerate(row):
        if v: arr[(y+q)*sc:(y+q+1)*sc, (x+q)*sc:(x+q+1)*sc] = 0
out = ROOT / "qr-tutorial.png"
Image.fromarray(arr).save(out, optimize=True)
text, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(out), cv2.IMREAD_GRAYSCALE))
print("目標：", url); print("解碼：", repr(text), "✓ 一致" if text == url else "✗ 不一致")
sys.exit(0 if text == url else 1)
