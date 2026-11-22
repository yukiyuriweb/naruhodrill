// ホーム画面に追加して使えるように（PWA）。service worker を登録する。
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
