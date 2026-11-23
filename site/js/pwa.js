// ホーム画面に追加して使えるように（PWA）。service worker を登録する。
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}

// タブレットで拡大させない。iPad の Safari は viewport の user-scalable=no を無視するので、ピンチ操作を止める。
// 拡大されると「こたえあわせ」などのボタンが画面の外に出てしまうため。
document.addEventListener("gesturestart", (e) => e.preventDefault());
document.addEventListener("touchmove", (e) => { if (e.touches.length > 1) e.preventDefault(); }, { passive: false });
