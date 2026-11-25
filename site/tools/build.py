# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""問題の検算・形式チェックと、公開用フォルダの作成。

    uv run site/tools/build.py          # チェックして site/data/index.json を作る（下書きも含む。開発用）
    uv run site/tools/build.py --dist   # さらに dist/ に公開する問題だけを書き出す

算数・論理パズル・空間把握の問題は、問題文の条件だけから答えを総当たりで求め直し、
答えが 1 つに決まること・JSON の答えと一致することを確かめる。
"""

import json
import re
import shutil
import sys
import unicodedata
from itertools import combinations, permutations, product
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "data"
DIST = SITE.parent / "dist"
SUBJECTS = ["math", "kokugo", "logic", "spatial"]

# 小1〜3 で習う漢字。これ以外の漢字には、ふりがな {漢字|かんじ} を付ける
KANJI_G1_3 = set("".join(
    line.split()[1] for line in (Path(__file__).parent / "kanji_g1-3.txt").read_text(encoding="utf-8").splitlines()
    if line[:1].isdigit()
))
RUBY_RE = re.compile(r"\{[^|{}]+\|[^|{}]+\}")
KANJI_RE = re.compile(r"[\u4e00-\u9fff]")


# 漢字パズルで部品として見せるもの（読みは選択肢に「氵（さんずい）」のように書く）
COMPONENTS = set("氵亻扌")


def unruby_kanji(t: str) -> set[str]:
    """ふりがなの付いていない、小4以降の漢字"""
    return {k for k in KANJI_RE.findall(RUBY_RE.sub("", t)) if k not in KANJI_G1_3 | COMPONENTS}


def norm(t: str) -> str:
    """答えの比較と字数かぞえ用。ふりがなを外し、全角・半角をそろえ、空白を除く（common.js の normalize と同じ）"""
    t = re.sub(r"\{([^|{}]+)\|[^|{}]+\}", r"\1", t).replace("**", "")
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", t))

# 算数の指針 2.2・5.2 の禁止事項
MATH_BANNED = ["面積", "cm2", "cm²", "°", "周長", "線分", "代入", "方程式", "%", "％", "割合",
               "四捨五入", "概数", "通分", "約分", "速さ", "円周率", "3.14"]
MATH_BANNED_RE = [
    re.compile(r"(?<![A-Za-z])[a-fh-ln-su-zA-Z](?![A-Za-z])\s*[=＝]"),  # 文字式（x＝ など。単位 g・m・t は除く）
    re.compile(r"\d\s*[:：]\s*\d"),  # 比
    re.compile(r"\d\s*度"),  # 角度（「もう一度」は対象外）
]
# 論理パズル・空間把握の指針 3 章の、言いかえる専門用語（算数の禁止事項にも従う）
TERMS_BANNED = {
    "logic": ["対偶", "背理法", "反例", "到達可能性", "グラフ"],
    "spatial": ["投影図", "鏡映", "対称軸", "回転対称", "体積", "表面積"],
}


# ---- 算数の検算（問題 ID ごと） ----

def math_001():
    # 円が たて2・よこ3 にぴったり。まわり 60cm。直径は 0.5cm 刻みで探す
    return [[d / 2, d / 4] for d in range(1, 400) if (3 * d / 2 + 2 * d / 2) * 2 == 60]


def math_002():
    # 7 でわると商 5、あまりあり
    ns = [n for n in range(1, 200) if n // 7 == 5 and n % 7 > 0]
    return [[min(ns), max(ns)]]


def math_003():
    # びん b + 水 w = 1200、b + w/2 = 750
    return [[w, b] for b in range(0, 1201) for w in range(0, 1201, 2) if b + w == 1200 and b + w // 2 == 750]


def perimeter(points):
    # 多角形の頂点（cm）を順にたどって、まわりの長さを出す
    return sum(abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))


def math_004():
    # たて6・よこ10 の長方形。ア：右上を たて2・よこ3 切り取る。イ：上の辺のまん中に はば2・ふかさ3 のみぞ
    a = perimeter([(0, 0), (10, 0), (10, 4), (7, 4), (7, 6), (0, 6)])
    b = perimeter([(0, 0), (10, 0), (10, 6), (6, 6), (6, 3), (4, 3), (4, 6), (0, 6)])
    return [[a, b]]


def math_005():
    # 十の位 a・一の位 b（1〜9）、ab + ba = 132。(1) a+b はどの解でも同じか (2) a-b=2 のときの ab
    pairs = [(a, b) for a in range(1, 10) for b in range(1, 10) if (10 * a + b) + (10 * b + a) == 132]
    sums = {a + b for a, b in pairs}
    nums = [10 * a + b for a, b in pairs if a - b == 2]
    return [[s, n] for s in sums for n in nums]


def math_006():
    # 30m に 5m おき。(1) かたがわ・両はしにも (2) 両がわ・両はしには うえない
    spots = list(range(0, 31, 5))
    return [[len(spots), (len(spots) - 2) * 2]]


def math_007():
    # バスは 7:10 から 15分おき。乗車 20分、学校まで 5分、8:30 までに着く。家からバスてい 8分
    buses = [7 * 60 + 10 + 15 * k for k in range(10)]
    ok = [b for b in buses if b + 20 + 5 <= 8 * 60 + 30]
    last = max(ok)
    leave = last - 8
    assert last // 60 == 7 and leave // 60 == 7  # 問題文が「7時何分」と聞いているため
    return [[last % 60, leave % 60]]


def math_008():
    # いちご 7目もり = 14人。みかん5・りんご4・ぶどう3
    bars = {"いちご": 7, "みかん": 5, "りんご": 4, "ぶどう": 3}
    unit = [u for u in range(1, 20) if bars["いちご"] * u == 14]
    return [[u, (bars["みかん"] - bars["ぶどう"]) * u, sum(bars.values()) * u] for u in unit]


def math_009():
    # 兄＋弟＝1000、兄＝弟＋200
    return [[y, a] for y in range(0, 1001) for a in range(0, 1001) if y + a == 1000 and a - y == 200]


def math_010():
    # 30円のあめ x こ、50円のガム y こ。x+y=8、30x+50y=300
    return [[y, x] for x in range(0, 9) for y in range(0, 9) if x + y == 8 and 30 * x + 50 * y == 300]


def math_011():
    # 公園を通る道 1400m、川ぞい 950m、家→公園 600m。(1) 公園→学校 (2) 行き公園・帰り川ぞい
    return [[x, 1400 + 950] for x in range(0, 1401) if 600 + x == 1400]


def math_012():
    # 30人が 4人がけの長いすに。(1) いる長いすの数 (2) さいごの長いすの人数
    n = min(k for k in range(1, 31) if 4 * k >= 30)
    return [[n, 30 - 4 * (n - 1)]]


def math_013():
    # ある数に 6 をたしたら 15。正しくは 6 をかける
    return [[n, n * 6] for n in range(0, 100) if n + 6 == 15]


def math_014():
    # 30cm のはり金で (1) 正三角形 (2) ちがう辺 8cm の二等辺三角形
    return [[e, s] for e in range(1, 31) for s in range(1, 31) if 3 * e == 30 and 2 * s + 8 == 30]


def math_015():
    # 0.1L を 1 として整数で。やかん 15、水とう 8 が 2つ
    left = 15 - 8
    return [[left / 10, (8 - left) / 10]]


def math_016():
    # 1辺 n こで正方形のまわりにならべる。実際に格子を数える
    def count(n):
        return sum(1 for i in range(n) for j in range(n) if i in (0, n - 1) or j in (0, n - 1))
    return [[count(5), count(10)]]


def math_017():
    # 3・0・7・1・5 で 5けた。(1) 最大 (2) 最小 (3) 50000 にいちばん近い
    from itertools import permutations
    ns = [int("".join(p)) for p in permutations("30715") if p[0] != "0"]
    best = min(abs(n - 50000) for n in ns)
    near = [n for n in ns if abs(n - 50000) == best]
    return [[max(ns), min(ns), x] for x in near]


def math_018():
    # ア6 × 7 ＝ イ2ウ
    return [[a, p] for a in range(1, 10) for p in [(10 * a + 6) * 7] if 100 <= p <= 999 and p // 10 % 10 == 2]


def math_019():
    # 8月1日が日曜日、31日まで。(3) は選択肢 ① 月 ② 火 ③ 水 ④ 木
    week = "日月火水木金土"
    sundays = [d for d in range(1, 32) if (d - 1) % 7 == 0]
    sep1 = week[31 % 7]
    return [[len(sundays), max(sundays), "月火水木".index(sep1) + 1]]


def math_020():
    # 32人。犬 12、ねこ 9、両方 4
    return [[d, n] for d in range(33) for c in range(33) for n in range(33)
            if d + 4 == 12 and c + 4 == 9 and d + c + 4 + n == 32]


# ---- 論理パズルの検算 ----

def logic_001():
    # 表に動物・うらに色のカード。見えている面：ねこ・いぬ・青・赤。ルール「ねこの うらは かならず 青」
    # (1) めくって たしかめないと いけない カード（選択肢 ① ねこ ② ねこと青 ③ ねこと赤 ④ ねこと青と赤）
    # (2) 青の カードの うらが いぬ なら ルールやぶりか（① はい ② いいえ）
    animals, colors = ["ねこ", "いぬ"], ["青", "赤"]
    breaks = lambda animal, color: animal == "ねこ" and color != "青"
    need = [f for f in animals if any(breaks(f, c) for c in colors)]
    need += [f for f in colors if any(breaks(a, f) for a in animals)]
    options = [["ねこ"], ["ねこ", "青"], ["ねこ", "赤"], ["ねこ", "青", "赤"]]
    return [[options.index(need) + 1, 1 if breaks("いぬ", "青") else 2]]


def logic_002():
    # 5人の かけっこ。(1) さくらは 何位 (2) 3位は だれ（① あおい ② かいと ③ さくら ④ だいち ⑤ えみ）
    from itertools import permutations
    names = ["あおい", "かいと", "さくら", "だいち", "えみ"]
    sols = []
    for order in permutations(names):
        r = {n: order.index(n) + 1 for n in order}
        if (r["えみ"] == r["あおい"] + 1 and r["かいと"] < r["さくら"] and r["だいち"] != 5
                and abs(r["だいち"] - r["さくら"]) == 1 and r["えみ"] < r["かいと"]):
            sols.append([r["さくら"], names.index(order[2]) + 1])
    return sols


def logic_003():
    # 3dL と 5dL の ます。入れる・すてる・うつす を 1回と数えて、4dL を 作る いちばん少ない回数
    def moves(s):
        a, b = s
        yield (3, b); yield (a, 5); yield (0, b); yield (a, 0)
        t = min(a, 5 - b); yield (a - t, b + t)
        t = min(b, 3 - a); yield (a + t, b - t)

    def shortest(start, steps):
        seen, frontier = {start}, [start]
        while frontier:
            if any(4 in s for s in frontier):
                return steps
            frontier = [n for s in frontier for n in moves(s) if n not in seen and not seen.add(n)]
            steps += 1
    return [[shortest((0, 0), 0)]]


def logic_004():
    # 8この石を、左の皿・右の皿・のせない石の3組に分ける。
    # あと1回で区別できるのは最大3こ。1こずつのせればその上限に届く。
    splits = [(per_pan, 8 - 2 * per_pan) for per_pan in range(1, 5)]
    return [[per_pan, off_scale] for per_pan, off_scale in splits if max(per_pan, off_scale) <= 3]


def logic_005():
    # はし番号の順。どの2本がこわれていると、2つの手がかりが両方成り立つか。
    bridges = dict(enumerate(["アイ", "アウ", "イウ", "イエ", "ウエ", "エオ"], 1))

    def reachable(start, broken):
        reached = {start}
        pending = [start]
        while pending:
            island = pending.pop()
            for number, (a, b) in bridges.items():
                if number in broken or island not in (a, b):
                    continue
                neighbor = b if island == a else a
                if neighbor not in reached:
                    reached.add(neighbor)
                    pending.append(neighbor)
        return reached

    options = [(1, 5), (4, 5), (1, 2), (1, 6)]
    return [[options.index(broken) + 1] for broken in combinations(bridges, 2)
            if "エ" not in reachable("ア", broken) and "オ" in reachable("イ", broken)]


def logic_006():
    # だんごとに花のあるマスを並べる。列はすべて異なり、ななめには接しない。
    blocked = {(2, 5), (4, 3)}
    answers = []
    for columns in permutations(range(1, 6)):
        if columns[0] != 2 or any(cell in blocked for cell in enumerate(columns, 1)):
            continue
        if all(abs(a - b) > 1 for a, b in zip(columns, columns[1:])):
            answers.append([columns[1], columns[3]])
    return answers


# ---- 空間把握の検算 ----

def roll_net(cells):
    """展開図（マス目の集まり）の上でサイコロを転がし、マスごとに どの面が下に来るかを返す"""
    turns = {(0, 1): "E", (0, -1): "W", (1, 0): "S", (-1, 0): "N"}
    opp = {"E": "W", "W": "E", "N": "S", "S": "N"}
    start = cells[0]
    faces = {start: "下"}
    stack = [(start, {d: d for d in ["上", "下", "E", "W", "N", "S"]})]
    while stack:
        (r, c), st = stack.pop()
        for (dr, dc), d in turns.items():
            n = (r + dr, c + dc)
            if n in cells and n not in faces:
                # d の向きへ転がると、d の面が下に、下の面が反対の向きに、反対の面が上に、上の面が d に行く
                new = dict(st)
                new["下"], new[opp[d]], new["上"], new[d] = st[d], st["下"], st[opp[d]], st["上"]
                faces[n] = new["下"]
                stack.append((n, new))
    return faces


def spatial_001():
    # かいだんの形の展開図。上のだん 左から 5・ア、まんなか 3・イ、下のだん 1・ウ。向かい合う目を たすと 7
    cells = [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3)]
    faces = roll_net(cells)
    pair = {"上": "下", "下": "上", "E": "W", "W": "E", "N": "S", "S": "N"}
    opposite = {a: b for a in cells for b in cells if faces[b] == pair[faces[a]]}
    given = {(0, 0): 5, (1, 1): 3, (2, 2): 1}
    blanks = [(0, 1), (1, 2), (2, 3)]  # ア・イ・ウ
    assert all(opposite[b] in given for b in blanks)
    return [[7 - given[opposite[b]] for b in blanks]]


def spatial_002():
    # 道の地図。たての道 x＝0〜3、よこの道 y＝0〜2（y は上が大きい）。どの道も 外がわに 1マス 出たところが はし
    # スタートは たての道 x＝1 の 下のはし、上を 向いて 立つ。
    # 「2つ目の かどを 右」「1つ目の かどを 右」「1つ目の かどを 左」「つきあたりまで」
    # 着く場所（① ア ② イ ③ ウ ④ エ）
    places = {(4, 0): 1, (-1, 0): 2, (4, 1): 3, (2, -1): 4}  # ア：y=0 の右はし、イ：y=0 の左はし、ウ：y=1 の右はし、エ：x=2 の下はし
    inside = lambda x, y: 0 <= x <= 3 and 0 <= y <= 2
    right = {(0, 1): (1, 0), (1, 0): (0, -1), (0, -1): (-1, 0), (-1, 0): (0, 1)}
    left = {v: k for k, v in right.items()}
    pos, d = (1, -1), (0, 1)
    for nth, turn in [(2, right), (1, right), (1, left)]:
        for _ in range(nth):
            pos = (pos[0] + d[0], pos[1] + d[1])
            assert inside(*pos)
        d = turn[d]
    while inside(*pos) or pos == (1, -1):
        pos = (pos[0] + d[0], pos[1] + d[1])
    return [[places[pos]]]


def spatial_003():
    # 立方体（1辺 1）を 頂点を通る 平らな面で 切った 切り口の形
    # ア(0,0,1) イ(1,0,1) ウ(1,1,1) エ(0,1,1) オ(0,0,0) カ(1,0,0) キ(1,1,0) ク(0,1,0)
    # (1) ア・ウ・カ (2) オ・カ・ウ・エ
    # 選択肢 ① 正三角形 ② 二等辺三角形 ③ 直角三角形 ④ 正方形 ⑤ 長方形
    V = {"ア": (0, 0, 1), "イ": (1, 0, 1), "ウ": (1, 1, 1), "エ": (0, 1, 1),
         "オ": (0, 0, 0), "カ": (1, 0, 0), "キ": (1, 1, 0), "ク": (0, 1, 0)}
    d2 = lambda p, q: sum((a - b) ** 2 for a, b in zip(p, q))
    dot = lambda p, q, r: sum((a - b) * (c - b) for a, b, c in zip(p, q, r))  # q の角が直角なら 0

    def shape(names):
        pts = [V[n] for n in names]  # 切り口を まわる 順に ならべてある
        n = len(pts)
        sides = [d2(pts[i], pts[(i + 1) % n]) for i in range(n)]
        rights = [dot(pts[i - 1], pts[i], pts[(i + 1) % n]) == 0 for i in range(n)]
        if n == 3:
            if len(set(sides)) == 1:
                return 1
            return 3 if any(rights) else 2
        assert all(rights)
        return 4 if len(set(sides)) == 1 else 5
    return [[shape(["ア", "ウ", "カ"]), shape(["オ", "カ", "ウ", "エ"])]]


def spatial_004():
    # 真上の図を、おくから手前へ。各列の最大が前、各行の最大が右から見た高さ。
    front = (2, 2, 3)
    right = (1, 3, 2)
    layouts = []
    for a, b, c, d, e, f in product(range(1, max(front) + 1), repeat=6):
        rows = ((a, 0, b), (0, c, d), (e, f, 0))
        if tuple(map(max, zip(*rows))) != front or tuple(map(max, reversed(rows))) != right:
            continue
        layouts.append((a, b, c, d, e, f))

    if not layouts:
        return []
    fewest = min(map(sum, layouts))
    return [[i, fewest] for i, heights in enumerate(zip(*layouts), 1) if len(set(heights)) > 1]


def spatial_005():
    # 一辺100、左上を原点とする。おった紙の右端 x=50 はおり目。
    # 半円の中心はおり目の上なので、左右で重なった中心は1つの丸い穴を表す。
    punch, edge_cut = (23, 23), (50, 38)
    folded = {punch, edge_cut}
    opened_down = folded | {(x, 100 - y) for x, y in folded}
    opened_right = opened_down | {(100 - x, y) for x, y in opened_down}
    corner_holes = {(x, y) for x in (23, 77) for y in (23, 77)}
    options = [
        corner_holes | {(x, y) for x in (0, 100) for y in (38, 62)},
        corner_holes | {(50, y) for y in (38, 62)},
        corner_holes | {(x, 50) for x in (38, 62)},
        corner_holes | {(x, y) for x in (42, 58) for y in (38, 62)},
    ]
    return [[i, len(opened_right)] for i, option in enumerate(options, 1) if option == opened_right]


def spatial_006():
    # マスの位置と、やじるし・ななめ線の向きを表す横方向の成分を反転する。
    # (列, 段, 形, 横向き)。ななめ線は下のはしから上のはしへの向き。
    original = {(0, 0, "やじるし", 1), (1, 1, "線", 1), (2, 1, "まる", 0)}
    mirrored = {(2 - col, row, shape, -dx) for col, row, shape, dx in original}
    options = [
        {(2, 0, "やじるし", 1), (1, 1, "線", 1), (0, 1, "まる", 0)},
        {(0, 0, "やじるし", -1), (1, 1, "線", -1), (2, 1, "まる", 0)},
        {(2, 0, "やじるし", -1), (1, 1, "線", -1), (0, 1, "まる", 0)},
        {(2, 1, "やじるし", -1), (1, 0, "線", 1), (0, 0, "まる", 0)},
    ]
    return [[i] for i, option in enumerate(options, 1) if option == mirrored]


SOLVERS = {f"math/{i:03d}": globals()[f"math_{i:03d}"] for i in range(1, 21)}
SOLVERS |= {f"{s}/{i:03d}": globals()[f"{s}_{i:03d}"] for s in ("logic", "spatial") for i in range(1, 7)}


def texts(p, for_child=True):
    yield p["title"]
    yield from p["body"]
    for part in p["parts"]:
        yield part["prompt"]
        for c in part.get("choices", []):
            yield c["label"]
    yield from p["hints"]
    yield from p["explanation"]
    for m in p.get("mistakes", []):
        yield m["message"]
    if not for_child:
        yield from p.get("parent_note", [])


def check(path: Path, subject: str) -> list[str]:
    errs = []
    p = json.loads(path.read_text(encoding="utf-8"))
    need = ["id", "subject", "status", "title", "lv", "area", "hint_interval_min", "body", "parts",
            "hints", "mistakes", "explanation", "parent_note"]
    errs += [f"{k} がない" for k in need if k not in p]
    if errs:
        return errs
    if p["id"] != path.stem or p["subject"] != subject:
        errs.append("id・subject がファイルの場所と合っていない")
    if p["status"] not in ("draft", "published"):
        errs.append(f"status が不正: {p['status']}")
    if not (isinstance(p["hint_interval_min"], int) and 1 <= p["hint_interval_min"] <= 10):
        errs.append("hint_interval_min は 1〜10 の整数")
    if len(p["hints"]) != 3:
        errs.append(f"ヒントが 3 つでない: {len(p['hints'])}")
    if p.get("figure") and not (SITE / p["figure"]).exists():
        errs.append(f"図がない: {p['figure']}")

    for i, part in enumerate(p["parts"]):
        a = part.get("answer", {})
        if a.get("type") == "number":
            if not isinstance(a.get("value"), (int, float)):
                errs.append(f"{part['label']} の答えが数でない")
        elif a.get("type") == "choice":
            values = [c["value"] for c in part.get("choices", [])]
            if a.get("value") not in values or len(set(values)) != len(values):
                errs.append(f"{part['label']} の選択肢と答えが合わない")
        elif a.get("type") == "text":
            v = a.get("value")
            if not (isinstance(v, str) and norm(v)) or not all(isinstance(x, str) for x in a.get("accept", [])):
                errs.append(f"{part['label']} の答えが文字でない")
                continue
            # 字数指定：答えの字数と、問題文の「◯字」が合っているか（1字の狂いもないこと）
            if "chars" in a:
                if len(norm(v)) != a["chars"]:
                    errs.append(f"{part['label']} の字数が合わない: 「{norm(v)}」は {len(norm(v))} 字、chars は {a['chars']}")
                if f"{a['chars']}字" not in norm(part["prompt"]):
                    errs.append(f"{part['label']} の問題文に「{a['chars']}字」がない")
            # 書きぬき：本文にそのままあるか。答えに小4以降の漢字を入れない（採点がぶれるため）
            if a.get("from_body"):
                if norm(v) not in norm("".join(p["body"])):
                    errs.append(f"{part['label']} の答え「{norm(v)}」が本文にそのままない")
                if RUBY_RE.search(v) or unruby_kanji(v):
                    errs.append(f"{part['label']} の書きぬきの答えに、小4以降の漢字がある")
        else:
            errs.append(f"{part['label']} の答えの形が不明: {a.get('type')}")
    for m in p["mistakes"]:
        if not (0 <= m["part"] < len(p["parts"])):
            errs.append(f"mistakes の part が範囲外: {m}")
        elif str(m["value"]) == str(p["parts"][m["part"]]["answer"]["value"]):
            errs.append(f"mistakes に正解が入っている: {m}")

    # 子どもが読む文（親向けメモは除く）：ふりがなと、指針の禁止事項
    for t in texts(p):
        if (ks := unruby_kanji(t)):
            errs.append(f"ふりがなが要る漢字 {''.join(sorted(ks))}: {t}")
        if subject != "kokugo":
            errs += [f"禁止語「{w}」: {t}" for w in MATH_BANNED + TERMS_BANNED.get(subject, []) if w in t]
            errs += [f"禁止パターン {r.pattern}: {t}" for r in MATH_BANNED_RE if r.search(t)]
    for t in texts(p, for_child=False):
        if t.count("{") != t.count("}") or t.count("**") % 2:
            errs.append(f"ふりがな・太字の記号が閉じていない: {t}")

    if subject != "kokugo":
        solver = SOLVERS.get(f"{subject}/{p['id']}")
        if solver is None:
            errs.append("検算の関数がない（SOLVERS に追加すること）")
        else:
            sols = solver()
            given = [part["answer"]["value"] for part in p["parts"]]
            if len(sols) != 1:
                errs.append(f"答えが 1 つに決まらない: {sols}")
            elif [float(x) for x in sols[0]] != [float(x) for x in given]:
                errs.append(f"答えが違う: 検算 {sols[0]} / JSON {given}")
    return errs


def main():
    index = {s: [] for s in SUBJECTS}
    bad = 0
    for subject in SUBJECTS:
        for path in sorted((DATA / subject).glob("[0-9][0-9][0-9].json")):
            errs = check(path, subject)
            print(f"{subject}/{path.name}: {'OK' if not errs else 'NG'}")
            for e in errs:
                print(f"  - {e}")
            bad += bool(errs)
            p = json.loads(path.read_text(encoding="utf-8"))
            index[subject].append({k: p.get(k) for k in ("id", "title", "lv", "area", "status")})
    (DATA / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if bad:
        sys.exit(1)

    if "--dist" in sys.argv:
        # 公開用：下書きの問題と開発用ファイルを除いて dist/ に書き出す
        if DIST.exists():
            shutil.rmtree(DIST)
        shutil.copytree(SITE, DIST, ignore=shutil.ignore_patterns("tools", "data", "review.html", "access.html", ".DS_Store"))
        published = {s: [x for x in index[s] if x["status"] == "published"] for s in SUBJECTS}
        for s in SUBJECTS:
            (DIST / "data" / s).mkdir(parents=True, exist_ok=True)
            for x in published[s]:
                shutil.copy(DATA / s / f"{x['id']}.json", DIST / "data" / s / f"{x['id']}.json")
        (DIST / "data" / "index.json").write_text(json.dumps(published, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"dist/ に書き出しました（公開: {sum(len(v) for v in published.values())} 問）")


if __name__ == "__main__":
    main()
