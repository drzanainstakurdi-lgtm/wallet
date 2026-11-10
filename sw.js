// Service worker: offline page + fast static files. Never caches pages with your data.
const V = 'wallet-v2';
const SHELL = ['/offline', '/static/icons/icon-192.png', '/static/icons/apple-touch-icon.png'];
const CDN = ['cdn.jsdelivr.net', 'fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET') return;
  if (r.mode === 'navigate') {                       // pages: network first, offline page as fallback
    e.respondWith(fetch(r).catch(() => caches.match('/offline')));
    return;
  }
  if (u.origin === location.origin && (u.pathname.startsWith('/static/') || u.pathname === '/app.css')) {   // icons: cache first
    e.respondWith(caches.match(r).then(m => m || fetch(r).then(res => {
      const c = res.clone(); caches.open(V).then(ca => ca.put(r, c)); return res; })));
    return;
  }
  if (CDN.includes(u.hostname)) {                    // chart library + fonts: stale while revalidate
    e.respondWith(caches.open(V).then(ca => ca.match(r).then(m => {
      const net = fetch(r).then(res => { ca.put(r, res.clone()); return res; }).catch(() => m);
      return m || net; })));
  }
});
