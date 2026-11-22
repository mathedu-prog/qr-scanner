/* ============================================================
   Scanly Service Worker
   - VERSION：每次發佈更新請遞增（tools/build.py --bump 會自動處理）
   - 頁面導覽：網路優先，離線時退回快取
   - 靜態資源：先回快取，同時背景更新（stale-while-revalidate）
   - 新版安裝後進入 waiting，等頁面以 postMessage("SKIP_WAITING") 通知才接管
============================================================ */
const VERSION = '1.0.0';
const CACHE_PREFIX = 'scanly-';
const CACHE_NAME = CACHE_PREFIX + VERSION;

// 預先快取的核心檔案（相對路徑，部署在 /<repo>/ 子目錄也能運作）
const CORE_ASSETS = [
  './',
  './index.html',
  './install.html',
  './manifest.json',
  './jsQR.js',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './apple-touch-icon.png',
  './qr-install.png'
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    // 逐一加入：單一檔案失敗不會讓整個安裝失敗；cache:'reload' 避開瀏覽器 HTTP 快取
    await Promise.all(CORE_ASSETS.map(url =>
      cache.add(new Request(url, { cache: 'reload' })).catch(err => console.warn('[SW] 預先快取失敗：', url, err))
    ));
  })());
  // 不自動 skipWaiting：讓使用者在畫面上確認「立即更新」
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith(CACHE_PREFIX) && k !== CACHE_NAME).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', event => {
  const d = event.data;
  if (d === 'SKIP_WAITING' || (d && d.type === 'SKIP_WAITING')) self.skipWaiting();
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;           // 不處理跨來源請求

  if (req.mode === 'navigate') {                              // 頁面導覽：網路優先
    event.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        if (fresh && fresh.ok) { const c = await caches.open(CACHE_NAME); c.put(req, fresh.clone()).catch(() => {}); }
        return fresh;
      } catch (err) {
        const cached = await caches.match(req, { ignoreSearch: true });
        return cached || (await caches.match('./index.html')) || (await caches.match('./')) ||
          new Response('目前離線，且尚未快取此頁面。', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
      }
    })());
    return;
  }

  event.respondWith((async () => {                            // 靜態資源：先回快取、背景更新
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(req, { ignoreSearch: true });
    const network = fetch(req).then(res => {
      if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
      return res;
    }).catch(() => null);
    if (cached) { event.waitUntil(network); return cached; }
    const res = await network;
    return res || new Response('', { status: 504, statusText: 'Offline' });
  })());
});
