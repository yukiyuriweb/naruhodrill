// 記録はこのブラウザの IndexedDB にだけ保存する（サーバーには送らない）。
//   attempts: 解いた記録 1 回分ずつ
//   sessions: 解いている途中の問題（開いた時刻・開いたヒント）。ヒントの待ち時間を再読み込みで戻さないため。

const DB_NAME = "naruhodrill";
const VERSION = 1;
let dbPromise = null;

function open() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        const attempts = db.createObjectStore("attempts", { keyPath: "id", autoIncrement: true });
        attempts.createIndex("key", "key");
        db.createObjectStore("sessions", { keyPath: "key" });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return dbPromise;
}

async function run(store, mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode);
    const req = fn(tx.objectStore(store));
    tx.oncomplete = () => resolve(req && req.result);
    tx.onerror = () => reject(tx.error);
  });
}

export const addAttempt = (a) => run("attempts", "readwrite", (s) => s.add(a));
export const deleteAttempt = (id) => run("attempts", "readwrite", (s) => s.delete(id));
export const getAttempt = (id) => run("attempts", "readonly", (s) => s.get(id));

// 新しい順
export async function allAttempts() {
  const list = await run("attempts", "readonly", (s) => s.getAll());
  return list.sort((a, b) => b.id - a.id);
}

export const getSession = (key) => run("sessions", "readonly", (s) => s.get(key));
export const putSession = (session) => run("sessions", "readwrite", (s) => s.put(session));
export const deleteSession = (key) => run("sessions", "readwrite", (s) => s.delete(key));

// ---- 書き出し・読み込み ----

export async function exportData() {
  return { app: DB_NAME, version: 1, exportedAt: new Date().toISOString(), attempts: await allAttempts() };
}

// 読み込んだ記録を足す。同じ問題・同じ提出時刻の記録はすでにあるものとして飛ばす。
export async function importData(data) {
  if (data?.app !== DB_NAME || !Array.isArray(data.attempts)) throw new Error("このドリルの記録ファイルではありません");
  const have = new Set((await allAttempts()).map((a) => `${a.key}|${a.submittedAt}`));
  let added = 0;
  for (const a of data.attempts.slice().reverse()) {
    if (have.has(`${a.key}|${a.submittedAt}`)) continue;
    const { id, ...rest } = a;
    await addAttempt(rest);
    added++;
  }
  return added;
}
