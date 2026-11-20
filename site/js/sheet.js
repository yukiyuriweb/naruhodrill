// 問題の「紙」と手書き。紙は 1000×707（A4 横の比率）の固定サイズで組み、画面に合わせて transform で縮める。
// 手書きの座標は紙に対する割合（0〜1）で持つので、どの画面でも同じ位置に出る。

import { richText, normalize } from "./common.js";

export const SHEET_W = 1000;
export const SHEET_H = 707; // ふつうの紙（A4 横の比率）

// 紙の高さ。文章の長い問題（layout: "reading"）は、問題ごとに sheet_h で高くできる
export function sheetHeight(problem) {
  return problem.sheet_h || SHEET_H;
}

// 画面（または要素）に収まる紙の幅
export function fitWidth(availW, availH, problem) {
  return Math.max(320, Math.min(availW, availH * (SHEET_W / sheetHeight(problem))));
}

// opts: width, editable, answers, marks, showCorrect
// 返り値: { ink, getAnswers(), setMarks(marks), setAnswers(answers), lock() }
export function renderSheet(container, problem, opts) {
  const s = opts.width / SHEET_W;
  container.classList.add("sheet-wrap");
  container.style.width = `${SHEET_W * s}px`;
  const H = sheetHeight(problem);
  container.style.height = `${H * s}px`;

  const partHtml = (p, i) => {
    let field;
    if (p.answer.type === "choice") {
      // 選択肢が長いときは、たてに ならべる
      const long = p.choices.some((c) => c.label.replace(/\{([^|{}]+)\|[^|{}]+\}/g, "$1").length > 8);
      field = `<div class="choices ${long ? "long" : ""}" data-i="${i}">${p.choices
        .map((c) => `<button type="button" class="choice" data-v="${c.value}">${richText(c.label)}</button>`)
        .join("")}</div>`;
    } else {
      field = `<input class="ans" inputmode="decimal" autocomplete="off" data-i="${i}">`;
    }
    if (p.answer.type === "text") {
      // ことばで答える欄。字数の決まった問題は、いま何字かを横に出す
      const w = Math.min(400, 60 + 26 * (p.answer.chars || 8));
      field = `<input class="ans text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-i="${i}" style="width:${w}px">`
        + (p.answer.chars ? `<span class="count" data-i="${i}"></span>` : "");
    }
    const correct = opts.showCorrect
      ? `<div class="correct">せいかい: ${richText(answerText(p))}</div>` : "";
    return `<div class="part">
      <div class="q"><span class="lbl">${richText(p.label)}</span> ${richText(p.prompt)}</div>
      <div class="row">${field}${p.unit ? `<span class="unit">${richText(p.unit)}</span>` : ""}<span class="mk" data-i="${i}"></span></div>
      <div class="msg" data-i="${i}"></div>
      ${correct}
    </div>`;
  };

  // 読解（layout: "reading"）は、設問を左右 2 列に分ける。前半を左、後半を右。col: 1 / 2 で問題ごとに変えられる
  let partsHtml = problem.parts.map(partHtml).join("");
  if (problem.layout === "reading") {
    const half = Math.ceil(problem.parts.length / 2);
    const colOf = (p, i) => p.col || (i < half ? 1 : 2);
    partsHtml = [1, 2].map((c) =>
      `<div class="col">${problem.parts.map((p, i) => (colOf(p, i) === c ? partHtml(p, i) : "")).join("")}</div>`).join("");
  }

  container.innerHTML = `
    <div class="sheet ${problem.layout === "reading" ? "reading" : ""}" style="height: ${H}px; transform: scale(${s})">
      <div class="s-head"><span class="s-title"></span><span class="lv">${richText(problem.lv)}</span></div>
      <div class="s-left">
        ${problem.body.map((b) => `<p>${richText(b)}</p>`).join("")}
        ${problem.figure ? `<img class="fig" src="${problem.figure}" alt="">` : ""}
      </div>
      <div class="s-right">
        ${partsHtml}
        <div class="memo">しきや 図を かいてね</div>
      </div>
      <canvas class="ink"></canvas>
    </div>`;
  container.querySelector(".s-title").innerHTML = richText(`${Number(problem.id)}. ${problem.title}`);

  const ink = container.querySelector(".ink");
  const dpr = window.devicePixelRatio || 1;
  ink.width = SHEET_W * s * dpr;
  ink.height = H * s * dpr;
  ink.style.height = `${H}px`;

  const inputs = [...container.querySelectorAll("input.ans")];
  const choiceGroups = [...container.querySelectorAll(".choices")];
  let locked = !opts.editable;

  const countChars = () =>
    container.querySelectorAll(".count").forEach((el) => {
      const v = container.querySelector(`input.ans[data-i="${el.dataset.i}"]`).value;
      el.textContent = `${[...normalize(v)].length}字`;
    });
  container.addEventListener("input", countChars);

  const setAnswers = (answers) => {
    problem.parts.forEach((p, i) => {
      const v = answers?.[i] ?? "";
      if (p.answer.type === "choice") {
        container.querySelectorAll(`.choices[data-i="${i}"] .choice`).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
      } else {
        container.querySelector(`input.ans[data-i="${i}"]`).value = v;
      }
    });
    countChars();
  };

  const getAnswers = () =>
    problem.parts.map((p, i) => {
      if (p.answer.type === "choice") {
        return container.querySelector(`.choices[data-i="${i}"] .choice.on`)?.dataset.v ?? "";
      }
      return container.querySelector(`input.ans[data-i="${i}"]`).value.trim();
    });

  choiceGroups.forEach((g) =>
    g.addEventListener("click", (e) => {
      const b = e.target.closest(".choice");
      if (!b || locked) return;
      g.querySelectorAll(".choice").forEach((x) => x.classList.toggle("on", x === b));
    })
  );

  const setMarks = (marks, messages = []) => {
    container.querySelectorAll(".mk").forEach((el) => {
      const m = marks ? marks[Number(el.dataset.i)] : undefined;
      el.textContent = m === undefined ? "" : m ? "○" : "×";
      el.className = `mk ${m === undefined ? "" : m ? "mark-correct" : "mark-wrong"}`;
    });
    container.querySelectorAll(".msg").forEach((el) => {
      const m = messages.find((x) => x.part === Number(el.dataset.i));
      el.innerHTML = m ? richText(m.message) : "";
    });
  };

  const lock = () => {
    locked = true;
    inputs.forEach((el) => (el.disabled = true));
  };

  setAnswers(opts.answers);
  setMarks(opts.marks);
  if (locked) lock();
  return { ink, getAnswers, setMarks, setAnswers, lock };
}

export function answerText(part) {
  const a = part.answer;
  if (a.type === "choice") return part.choices.find((c) => c.value === a.value)?.label ?? a.value;
  return `${a.value}${part.unit ? " " + part.unit : ""}`;
}

// ---- 手書き ----

export function drawAll(canvas, strokes) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  for (const st of strokes) {
    const pts = st.points;
    if (!pts.length) continue;
    ctx.strokeStyle = ctx.fillStyle = st.color;
    ctx.lineWidth = st.width * w;
    ctx.lineCap = ctx.lineJoin = "round";
    ctx.beginPath();
    if (pts.length === 1) {
      ctx.arc(pts[0][0] * w, pts[0][1] * h, ctx.lineWidth / 2, 0, Math.PI * 2);
      ctx.fill();
      continue;
    }
    ctx.moveTo(pts[0][0] * w, pts[0][1] * h);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0] * w, pts[i][1] * h);
    ctx.stroke();
  }
}

// Apple Pencil・マウス・指で書けるようにする。Pencil を一度使ったら、指の入力は無視する（手のひら対策）。
export function attachPen(ink, strokes, getColor) {
  let current = null;
  let penSeen = false;
  const pointOf = (e) => {
    const r = ink.getBoundingClientRect();
    return [+((e.clientX - r.left) / r.width).toFixed(4), +((e.clientY - r.top) / r.height).toFixed(4),
            +(e.pressure || 0.5).toFixed(2), Math.round(e.timeStamp)];
  };
  const accept = (e) => {
    if (e.pointerType === "pen") penSeen = true;
    return !(e.pointerType === "touch" && penSeen);
  };
  ink.addEventListener("pointerdown", (e) => {
    if (!accept(e)) return;
    document.activeElement?.blur?.(); // 答えの欄から手書きに戻ったらキーボードを閉じる
    ink.setPointerCapture(e.pointerId);
    current = { color: getColor(), width: 0.0035, points: [pointOf(e)] };
    strokes.push(current);
    drawAll(ink, strokes);
  });
  ink.addEventListener("pointermove", (e) => {
    if (!current || !accept(e)) return;
    for (const ev of e.getCoalescedEvents ? e.getCoalescedEvents() : [e]) current.points.push(pointOf(ev));
    drawAll(ink, strokes);
  });
  const end = () => (current = null);
  ink.addEventListener("pointerup", end);
  ink.addEventListener("pointercancel", end);
}
