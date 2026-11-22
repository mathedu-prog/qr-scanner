#!/usr/bin/env python3
"""產生安裝教學頁 install.html 與 qr-install.png，並實際解碼驗證 QR Code 內容。

用法：
  python3 tools/build.py <GitHub帳號> <repo名稱> [--bump]
  python3 tools/build.py --url https://example.com/app/ [--bump]

  --bump  同步把 sw.js 的 VERSION 與 index.html 的 APP_VERSION patch 版號 +1
          （每次推送更新前都要執行，已安裝的使用者才會看到「有新版本可用」）

需求：pip install qrcode pillow opencv-python（opencv 用於解碼驗證）
"""
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "https://YOUR_ACCOUNT.github.io/qr-scanner/"


# ---------- 參數 ----------
def parse_args(argv):
    bump = "--bump" in argv
    args = [a for a in argv if a != "--bump"]
    if "--url" in args:
        url = args[args.index("--url") + 1]
    elif len(args) >= 2:
        url = f"https://{args[0]}.github.io/{args[1]}/"
    else:
        url = PLACEHOLDER
    if not url.endswith("/"):
        url += "/"
    return url, bump


# ---------- QR 產生 ----------
def make_matrix(url):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0, box_size=1)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.get_matrix()  # list[list[bool]]，不含安靜區


def matrix_to_svg(m, quiet=4):
    """內嵌 SVG：白底 + 黑色模組，每列把連續模組合併成一段 path，檔案小且邊緣銳利"""
    n = len(m)
    size = n + quiet * 2
    segs = []
    for y, row in enumerate(m):
        x = 0
        while x < n:
            if row[x]:
                s = x
                while x < n and row[x]:
                    x += 1
                segs.append(f"M{s + quiet} {y + quiet}h{x - s}v1h-{x - s}z")
            else:
                x += 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" role="img" '
            f'aria-label="安裝 Scanly 的 QR Code" shape-rendering="crispEdges">'
            f'<rect width="{size}" height="{size}" fill="#fff"/><path fill="#000" d="{"".join(segs)}"/></svg>')


def matrix_to_png(m, path, quiet=4, scale=16):
    n = len(m)
    size = (n + quiet * 2) * scale
    arr = np.full((size, size), 255, np.uint8)
    for y, row in enumerate(m):
        for x, v in enumerate(row):
            if v:
                arr[(y + quiet) * scale:(y + quiet + 1) * scale, (x + quiet) * scale:(x + quiet + 1) * scale] = 0
    Image.fromarray(arr).save(path, optimize=True)


# ---------- 解碼驗證 ----------
def decode_gray(gray):
    det = cv2.QRCodeDetector()
    text, _, _ = det.detectAndDecode(gray)
    return text


def verify(url, html_path, png_path):
    ok = True
    # 1) PNG
    png = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
    t1 = decode_gray(png)
    print(f"PNG 解碼：{t1!r} -> {'✓ 一致' if t1 == url else '✗ 不一致'}")
    ok &= t1 == url
    # 2) 從 install.html 內嵌 SVG 的 path 還原點陣後解碼（驗證實際輸出的 SVG）
    html = html_path.read_text(encoding="utf-8")
    vb = re.search(r'<svg[^>]*viewBox="0 0 (\d+) \1"[^>]*aria-label="安裝 Scanly 的 QR Code"', html)
    d = re.search(r'<path fill="#000" d="([^"]+)"', html)
    size = int(vb.group(1))
    sc = 12
    arr = np.full((size * sc, size * sc), 255, np.uint8)
    for x, y, w in re.findall(r"M(\d+) (\d+)h(\d+)v1h-\d+z", d.group(1)):
        x, y, w = int(x), int(y), int(w)
        arr[y * sc:(y + 1) * sc, x * sc:(x + w) * sc] = 0
    t2 = decode_gray(arr)
    print(f"SVG 解碼：{t2!r} -> {'✓ 一致' if t2 == url else '✗ 不一致'}")
    ok &= t2 == url
    # 3) 頁面上的連結與顯示文字
    link_ok = f'href="{url}"' in html and f'>{url}</code>' in html
    print(f"頁面連結/顯示文字：{'✓ 一致' if link_ok else '✗ 不一致'}")
    ok &= link_ok
    return ok


# ---------- 版本遞增 ----------
def bump_version():
    sw = ROOT / "sw.js"
    s = sw.read_text(encoding="utf-8")
    m = re.search(r"const VERSION = '(\d+)\.(\d+)\.(\d+)'", s)
    new = f"{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"
    sw.write_text(s.replace(m.group(0), f"const VERSION = '{new}'"), encoding="utf-8")
    idx = ROOT / "index.html"
    t = idx.read_text(encoding="utf-8")
    t = re.sub(r"const APP_VERSION = '[\d.]+'", f"const APP_VERSION = '{new}'", t)
    idx.write_text(t, encoding="utf-8")
    print(f"版本遞增：{m.group(0).split(chr(39))[1]} -> {new}")


# ---------- install.html 模板 ----------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<!-- 此檔由 tools/build.py 產生；請改 build.py 的模板後重新執行，勿直接手改。 -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>安裝 Scanly · QR 掃描器</title>
<meta name="theme-color" content="#0A0C10">
<meta name="color-scheme" content="dark light">
<link rel="icon" type="image/png" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
:root{--bg:#0A0C10;--surface:#14171E;--surface2:#1B1F28;--text:#F2F4F8;--muted:#8B93A3;--line:rgba(255,255,255,.09);--accent:#4C8DFF;--accent-soft:rgba(76,141,255,.16);--ok:#34D399;
  --font:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang TC","Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif}
@media (prefers-color-scheme:light){:root{--bg:#F3F5F9;--surface:#fff;--surface2:#F0F2F7;--text:#0E1116;--muted:#667085;--line:rgba(15,20,30,.1);--accent:#2F6BFF;--accent-soft:rgba(47,107,255,.12);--ok:#0E9F6E}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{background:var(--bg);color:var(--text);font-family:var(--font);-webkit-text-size-adjust:100%}
body{margin:0;padding:max(20px,env(safe-area-inset-top)) 16px max(32px,env(safe-area-inset-bottom));min-height:100dvh}
main{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
.ic{width:20px;height:20px;flex:none;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;vertical-align:-4px}
header{display:flex;align-items:center;gap:14px;padding-top:6px}
header img{width:60px;height:60px;border-radius:15px}
h1{margin:0;font-size:28px;letter-spacing:-.02em}
header p{margin:2px 0 0;color:var(--muted);font-size:14px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:20px}
.qr-card{display:grid;grid-template-columns:auto 1fr;gap:24px;align-items:center}
.qr{width:208px;height:208px;border-radius:16px;overflow:hidden;background:#fff;padding:0;box-shadow:0 2px 12px rgba(0,0,0,.2)}
.qr svg{display:block;width:100%;height:100%}
.qr-info h2{margin:0 0 6px;font-size:18px}
.qr-info p{margin:0 0 10px;color:var(--muted);font-size:14px;line-height:1.6}
code{display:block;padding:10px 12px;border-radius:12px;background:var(--surface2);font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;word-break:break-all;margin-bottom:14px}
.btns{display:flex;flex-wrap:wrap;gap:10px}
.btn{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 16px;border-radius:14px;border:0;background:var(--surface2);color:var(--text);font:600 14px var(--font);cursor:pointer;text-decoration:none}
.btn.primary{background:var(--accent);color:#fff}
.btn:active{transform:scale(.97)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.seg{display:flex;gap:4px;background:var(--surface2);padding:4px;border-radius:14px;margin-bottom:16px}
.seg button{flex:1;display:flex;align-items:center;justify-content:center;gap:6px;min-height:40px;border:0;border-radius:11px;background:none;color:var(--muted);font:600 14px var(--font);cursor:pointer}
.seg button[aria-selected="true"]{background:var(--surface);color:var(--text);box-shadow:0 1px 4px rgba(0,0,0,.18)}
.panel{display:none}.panel.on{display:block}
.panel h3{margin:0 0 4px;font-size:17px}
.panel .sub{margin:0 0 14px;color:var(--muted);font-size:13.5px}
ol{margin:0;padding:0;list-style:none;counter-reset:s;display:flex;flex-direction:column;gap:12px}
li{counter-increment:s;display:flex;gap:12px;font-size:15px;line-height:1.6}
li::before{content:counter(s);flex:none;width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent);font-size:13px;font-weight:700;margin-top:1px}
li .ic{color:var(--accent);margin:0 2px}
.note{margin:16px 0 0;padding:12px 14px;border-radius:14px;background:var(--surface2);color:var(--muted);font-size:13px;line-height:1.6}
.ok{display:flex;gap:10px;align-items:flex-start;color:var(--ok);font-size:14px;line-height:1.6}
footer{text-align:center;color:var(--muted);font-size:12.5px;padding:6px 0}
#toast{position:fixed;left:50%;bottom:max(24px,env(safe-area-inset-bottom));transform:translate(-50%,20px);background:var(--text);color:var(--bg);padding:10px 16px;border-radius:12px;font-size:14px;font-weight:600;opacity:0;pointer-events:none;transition:.25s}
#toast.on{opacity:1;transform:translate(-50%,0)}
@media (max-width:560px){.qr-card{grid-template-columns:1fr;justify-items:center;text-align:center}.qr{width:min(260px,100%);height:auto;aspect-ratio:1}.btns{justify-content:center}.qr-info{width:100%}}
@media print{
  html,body{background:#fff!important;color:#000!important}
  .seg,.btns,#toast,footer{display:none!important}
  .card{border:1px solid #ccc;box-shadow:none;break-inside:avoid}
  .panel{display:block!important;margin-bottom:12px}.seg+.panel,.panel{page-break-inside:avoid}
  .qr{width:260px;height:260px}code{background:#f3f3f3;color:#000}
}
</style>
</head>
<body>
<main>
  <header>
    <img src="icon-192.png" alt="Scanly 圖示" width="60" height="60">
    <div><h1>安裝 Scanly</h1><p>像原生 App 一樣使用，離線也能掃描。</p></div>
  </header>

  <section class="card qr-card" aria-label="安裝 QR Code">
    <div class="qr">{{QR_SVG}}</div>
    <div class="qr-info">
      <h2>用手機掃描這個 QR Code</h2>
      <p>開啟相機或任何掃描器，掃描後在瀏覽器開啟，再依下方步驟加入主畫面。</p>
      <code>{{URL}}</code>
      <div class="btns">
        <button class="btn primary" id="copy"><svg class="ic" viewBox="0 0 24 24"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>複製連結</button>
        <a class="btn" href="{{URL}}" target="_blank" rel="noopener"><svg class="ic" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>直接開啟</a>
        <button class="btn" id="print"><svg class="ic" viewBox="0 0 24 24"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>列印此頁</button>
      </div>
    </div>
  </section>

  <section class="card" aria-label="安裝步驟">
    <div class="seg" role="tablist" aria-label="選擇裝置">
      <button role="tab" id="t-ios" aria-selected="false" aria-controls="p-ios"><svg class="ic" viewBox="0 0 24 24"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/></svg>iPhone／iPad</button>
      <button role="tab" id="t-android" aria-selected="false" aria-controls="p-android"><svg class="ic" viewBox="0 0 24 24"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/></svg>Android</button>
      <button role="tab" id="t-desktop" aria-selected="false" aria-controls="p-desktop"><svg class="ic" viewBox="0 0 24 24"><rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></svg>電腦</button>
    </div>

    <div class="panel" id="p-ios" role="tabpanel" aria-labelledby="t-ios">
      <h3>iPhone／iPad（Safari）</h3>
      <p class="sub">請使用 Safari 開啟網址。</p>
      <ol>
        <li><span>用 Safari 開啟上方連結（掃描 QR Code 或按「直接開啟」）。</span></li>
        <li><span>點選「分享」按鈕<svg class="ic" viewBox="0 0 24 24"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" x2="12" y1="2" y2="15"/></svg>（iPhone 在畫面底部，iPad 在右上角；若看不到，先點網址列旁或底部的「⋯」）。</span></li>
        <li><span>向下捲動選單，點「加入主畫面」<svg class="ic" viewBox="0 0 24 24"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>。</span></li>
        <li><span>確認名稱後點右上角「新增」，主畫面就會出現 Scanly。</span></li>
      </ol>
      <p class="note">iOS 版本不同，選單位置可能略有差異；若沒有「加入主畫面」，請確認是用 Safari 開啟，而非應用程式內建瀏覽器。</p>
    </div>

    <div class="panel" id="p-android" role="tabpanel" aria-labelledby="t-android">
      <h3>Android（Chrome）</h3>
      <p class="sub">Samsung Internet 等瀏覽器的選單名稱可能不同。</p>
      <ol>
        <li><span>用 Chrome 開啟上方連結。</span></li>
        <li><span>點右上角選單「⋮」<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>。</span></li>
        <li><span>選擇「安裝應用程式」（部分版本為「加到主畫面」，再選「安裝」）。</span></li>
        <li><span>在確認視窗按「安裝」，之後可從主畫面或應用程式清單開啟。</span></li>
      </ol>
      <p class="note">若選單裡沒有安裝選項，請先在 Scanly 頁面停留幾秒並重新整理一次，Chrome 才會判定為可安裝。</p>
    </div>

    <div class="panel" id="p-desktop" role="tabpanel" aria-labelledby="t-desktop">
      <h3>電腦（Chrome／Edge）</h3>
      <p class="sub">Windows、macOS、Linux、ChromeOS 皆適用。</p>
      <ol>
        <li><span>用 Chrome 或 Edge 開啟上方連結。</span></li>
        <li><span>點網址列右側的「安裝」圖示<svg class="ic" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>。</span></li>
        <li><span>在彈出視窗按「安裝」，Scanly 會以獨立視窗開啟，並出現在開始功能表或應用程式清單。</span></li>
      </ol>
      <p class="note">沒看到圖示？也可從瀏覽器選單找「安裝 Scanly」或「將此網站安裝為應用程式」。Firefox 桌面版目前不支援安裝網頁 App；macOS Safari 17 以上可用「檔案 → 加入 Dock」。</p>
    </div>
  </section>

  <section class="card">
    <div class="ok"><svg class="ic" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg><span>安裝後可離線使用；有新版本時，App 內會顯示「有新版本可用．立即更新」。掃描全程只在你的裝置上處理，不會上傳影像。</span></div>
  </section>
  <footer>Scanly · 版本頁面連結：{{URL}}</footer>
</main>
<div id="toast" role="status"></div>

<script>
'use strict';
(function () {
  var URL_TEXT = "{{URL}}";
  function toast(msg) { var t = document.getElementById('toast'); t.textContent = msg; t.className = 'on'; setTimeout(function () { t.className = ''; }, 2000); }
  // 依裝置自動選擇分頁
  var ua = navigator.userAgent, ios = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var which = ios ? 'ios' : /android/i.test(ua) ? 'android' : 'desktop';
  function show(name) {
    ['ios', 'android', 'desktop'].forEach(function (n) {
      document.getElementById('p-' + n).classList.toggle('on', n === name);
      document.getElementById('t-' + n).setAttribute('aria-selected', String(n === name));
    });
  }
  ['ios', 'android', 'desktop'].forEach(function (n) { document.getElementById('t-' + n).addEventListener('click', function () { show(n); }); });
  show(which);
  document.getElementById('copy').addEventListener('click', function () {
    function fallback() {
      try { var ta = document.createElement('textarea'); ta.value = URL_TEXT; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select(); var ok = document.execCommand('copy'); document.body.removeChild(ta); toast(ok ? '已複製連結' : '複製失敗，請手動選取'); }
      catch (e) { toast('複製失敗，請手動選取'); }
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(URL_TEXT).then(function () { toast('已複製連結'); }, fallback); else fallback();
  });
  document.getElementById('print').addEventListener('click', function () { try { window.print(); } catch (e) { toast('此瀏覽器無法列印'); } });
})();
</script>
</body>
</html>
"""


def main():
    url, bump = parse_args(sys.argv[1:])
    if bump:
        bump_version()
    m = make_matrix(url)
    svg = matrix_to_svg(m)
    html_path = ROOT / "install.html"
    html_path.write_text(TEMPLATE.replace("{{QR_SVG}}", svg).replace("{{URL}}", url), encoding="utf-8")
    png_path = ROOT / "qr-install.png"
    matrix_to_png(m, png_path)
    print(f"目標網址：{url}")
    if url == PLACEHOLDER:
        print("⚠ 目前使用的是示意網址，請改用：python3 tools/build.py <帳號> <repo> 重新產生。")
    ok = verify(url, html_path, png_path)
    print("驗證結果：", "全部通過 ✓" if ok else "失敗 ✗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
