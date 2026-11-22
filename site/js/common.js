// 各ページで共有する小さな関数。

export const SITE_NAME = "なるほドリル";
export const SUBJECTS = { math: "さんすう", kokugo: "こくご", logic: "ろんり", spatial: "くうかん" };
export const RESULT_MARK = { correct: "○", partial: "△", wrong: "×", revealed: "－" };
export const RESULT_WORD = { correct: "せいかい！", partial: "おしい！", wrong: "ざんねん", revealed: "こたえを 見た" };

// 開発中（自分の Mac）だけ有効にする機能の判定
export const IS_LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);

const esc = (t) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// {漢字|かんじ} → ふりがな、**太字** → 太字。それ以外は文字としてそのまま出す。
export function richText(s) {
  return esc(String(s))
    .replace(/\{([^|{}]+)\|([^|{}]+)\}/g, "<ruby>$1<rt>$2</rt></ruby>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
}

export function plainText(s) {
  return String(s).replace(/\{([^|{}]+)\|[^|{}]+\}/g, "$1").replace(/\*\*/g, "");
}

export function fmt(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function problemKey(subject, id) {
  return `${subject}/${id}`;
}

export function problemUrl(subject, id) {
  return `problem.html?s=${subject}&id=${id}`;
}

export async function loadIndex() {
  return fetch("data/index.json", { cache: "no-cache" }).then((r) => r.json());
}

// 問題のある教科だけ（公開中の問題がない教科は出さない。開発中は下書きも数える）
export function visibleSubjects(index) {
  return Object.keys(SUBJECTS).filter((s) => (index[s] || []).some((p) => p.status === "published" || IS_LOCAL));
}

export async function loadProblem(subject, id) {
  if (!/^[a-z]+$/.test(subject) || !/^\d{3}$/.test(id)) throw new Error("bad id");
  const r = await fetch(`data/${subject}/${id}.json`, { cache: "no-cache" });
  if (!r.ok) throw new Error("not found");
  return r.json();
}

// 答えの比較用に、全角を半角にして空白を除く
export function normalize(s) {
  return String(s ?? "").normalize("NFKC").replace(/\s/g, "");
}

// 小問 1 つの正誤
export function checkPart(part, given) {
  const a = part.answer;
  if (a.type === "number") {
    const g = normalize(given);
    return g !== "" && Number(g) === Number(a.value);
  }
  if (a.type === "choice") return given === a.value;
  if (a.type === "text") {
    // 書きぬき・ことばで答える問題。空白と全角・半角のちがいは見ない。accept は別の書き方を認めるとき
    const g = normalize(given);
    return g !== "" && [a.value, ...(a.accept || [])].some((v) => normalize(v) === g);
  }
  return false;
}

export function grade(problem, answers) {
  const marks = problem.parts.map((p, i) => checkPart(p, answers[i]));
  const result = marks.every(Boolean) ? "correct" : marks.some(Boolean) ? "partial" : "wrong";
  return { result, marks };
}

// よくある間違いに合わせた一言（問題の mistakes に登録したもの）
export function mistakeMessages(problem, answers, marks) {
  const out = [];
  for (const m of problem.mistakes || []) {
    if (marks[m.part]) continue;
    const g = normalize(answers[m.part]);
    if (g !== "" && normalize(m.value) === g) out.push({ part: m.part, message: m.message });
  }
  return out;
}
