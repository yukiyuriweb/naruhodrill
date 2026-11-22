// オフラインでも開けるようにするための service worker。
// 問題や画面はよく更新するので、いつもネットワークを先に見て、つながらないときだけ保存しておいたものを使う。
const CACHE = "naruhodrill-v1";
const SHELL = ["./", "index.html", "problem.html", "records.html", "dashboard.html", "about.html",
  "css/style.css", "js/common.js", "js/db.js", "js/sheet.js", "js/pwa.js", "data/index.json",
  "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(async () => (await caches.match(req)) || (await caches.match(req, { ignoreSearch: true })) || Response.error())
  );
});
