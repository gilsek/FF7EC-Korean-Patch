#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FF7EC 한글패치용 용어집 초안(일본어 키)을 만든다.

공식 한국어 표기 근거는 FF7 리버스 공식 텍스트 짝(work/rebirth_text/jp_kr.tsv).
EC 현재 표기는 work/glossary/ec_terms_*.tsv 의 ko_variants(필요하면 EC 번역 짝에서
구(句) 단위로 보정)에서 가져온다.

출력 (새 파일만):
  work/glossary/glossary_draft.tsv
  work/glossary/glossary_diff.tsv

사용:
  python tools/build_glossary_draft.py
"""

from __future__ import annotations

import collections
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REBIRTH = os.path.join(ROOT, "work", "rebirth_text", "jp_kr.tsv")
GLOSS = os.path.join(ROOT, "work", "glossary")
GT = os.path.join(ROOT, "gt_project")
OUT_DRAFT = os.path.join(GLOSS, "glossary_draft.tsv")
OUT_DIFF = os.path.join(GLOSS, "glossary_diff.tsv")

csv.field_size_limit(1 << 30)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- 정규화

TAG_RE = re.compile(r"<[^>]*>")
WS_RE = re.compile(r"\s+")
# 앞뒤 공백/줄임표/문장부호 제거 (용어 비교용)
EDGE_RE = re.compile(r"^[\s　…‥！？!?。、,]+|[\s　…‥！？!?。、,]+$")

JP_QUOTE_RE = re.compile(r"[「『]([^「」『』]*)[」』]")
KO_QUOTE_RE = re.compile(r"[「『“\"]([^「」『』“”\"]*)[」』”\"]")


def clean_jp(s: str) -> str:
    s = TAG_RE.sub("", s)
    s = s.replace("\\n", " ")
    s = WS_RE.sub(" ", s).strip()
    return EDGE_RE.sub("", s)


def clean_ko(s: str) -> str:
    s = TAG_RE.sub("", s)
    s = s.replace("\\n", " ")
    s = WS_RE.sub(" ", s).strip()
    return EDGE_RE.sub("", s)


# ---------------------------------------------------------------- 한국어 토큰/구

KO_SEP = re.compile(r"[^가-힣A-Za-z0-9]+")
# 조사/어미. '로', '서', '만' 은 단어 끝 글자와 충돌하므로 넣지 않는다
# (마코로, 골드 소서, 바크만 보호).
SUF = [
    "으로", "에서", "에게", "까지", "부터", "보다", "처럼", "라고", "이라는",
    "이라", "라는", "이며", "이고", "인데", "이었던", "였던", "이었다", "였다",
    "이었", "였", "했습니다", "했습니", "합니다", "했습", "한다", "했다",
    "은", "는", "이", "가", "을", "를", "의", "에", "와", "과",
    "도", "들", "야", "요", "다", "며", "고", "면",
]
SUF_SORTED = sorted(SUF, key=len, reverse=True)

HONORIFIC = {"씨", "님", "군", "양"}

# 구(句) 선택에서 맥락어를 걸러내기 위한 최소 불용어. '월', '번', '만' 등은 넣지 않는다.
STOP_TOK = {
    "그", "이", "저", "나", "너", "우리", "너희", "당신", "자신", "사람", "녀석",
    "놈", "것", "거", "게", "수", "때", "줄", "데", "중", "더", "또", "잘", "안",
    "못", "왜", "뭐", "누구", "어디", "언제", "지금", "정말", "진짜", "아주", "너무",
    "모두", "전부", "다시", "아직", "이미", "계속", "먼저", "나중", "그냥", "조금",
    "많이", "하나", "둘", "이런", "그런", "저런", "어떤", "무슨", "그래", "그러나",
    "하지만", "그리고", "그래서", "그런데", "근데", "그럼", "그러면", "아니", "응",
    "어", "음", "아", "오", "와", "하하", "허허", "이제", "그게", "이게", "저게",
    "무엇", "어떻게", "그렇게", "이렇게", "저렇게", "같은",
}


KANA_RE = re.compile(r"[ァ-ヺーヽヾ]")
KANJI_RE = re.compile(r"[一-鿿]")


def allow_ext(term: str) -> bool:
    """공식/현재 표기를 여러 토큰으로 늘려 볼지.

    '・' 나 'の' 가 들어간 복합어, 한자+가나 혼합어, 5글자 이상 가타카나 복합어만
    늘린다. 2~4글자 단일 가타카나어나 순한자어는 늘리면 맥락어가 섞이기 쉽다.
    """
    if "・" in term or "の" in term:
        return True
    has_kana = bool(KANA_RE.search(term))
    has_kanji = bool(KANJI_RE.search(term))
    if has_kana and has_kanji:
        return True
    if has_kana and not has_kanji and len(term) >= 5:
        return True
    if has_kanji and not has_kana and len(term) >= 3:
        return True
    return False


def is_kana_only(term: str) -> bool:
    return bool(KANA_RE.search(term)) and not KANJI_RE.search(term)


# 한자어 뒤에 붙으면 다른 단어가 되는 꼬리(目的+地, 騎士+団, 一方+的 …).
KANJI_SUFFIX_BLOCK = set("的性化団地者")


def occurrence_ok(jp: str, term: str) -> bool:
    """용어가 다른 단어의 일부로만 걸린 행을 거른다.

    가타카나 용어는 앞뒤가 가타카나면(バカ/バカンス, チーム/ブルーチーム) 버리고,
    한자 용어는 目的/目的地, 騎士/騎士団, 一方/一方的 같은 파생 꼬리를 버린다.
    """
    kana_only = is_kana_only(term)
    kanji_only = bool(KANJI_RE.search(term)) and not bool(KANA_RE.search(term))
    for m in re.finditer(re.escape(term), jp):
        i, j = m.start(), m.end()
        prev = jp[i - 1] if i > 0 else ""
        nxt = jp[j] if j < len(jp) else ""
        if kana_only and (KANA_RE.match(prev or "") or KANA_RE.match(nxt or "")):
            continue
        if kanji_only and len(term) >= 2 and nxt in KANJI_SUFFIX_BLOCK:
            continue
        return True
    return False


def stems(ko: str) -> list:
    out = []
    for t in KO_SEP.split(ko):
        if not t:
            continue
        for s in SUF_SORTED:
            if len(t) > len(s) and t.endswith(s):
                t = t[: -len(s)]
                break
        if t:
            out.append(t)
    return out


def grams(ko: str, nmax: int = 3) -> set:
    ts = stems(ko)
    g = set()
    for i in range(len(ts)):
        for n in range(1, nmax + 1):
            if i + n <= len(ts):
                g.add(" ".join(ts[i : i + n]))
    return g


# ---------------------------------------------------------------- 자료 읽기

def load_tsv(name: str) -> list:
    path = os.path.join(GLOSS, name)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def top_variant(s: str) -> str:
    if not s:
        return ""
    m = re.match(r"^([^;]+?)\((\d+),(\d+)%\)", s.strip())
    if m:
        return m.group(1).strip()
    return s.split(";")[0].strip()


def load_rebirth():
    exact = collections.defaultdict(collections.Counter)
    short = []
    with open(REBIRTH, encoding="utf-8-sig", newline="") as f:
        rdr = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rdr, None)
        for row in rdr:
            if len(row) < 5:
                continue
            jp_raw = row[3]
            kr_raw = "\t".join(row[4:])
            jp = clean_jp(jp_raw)
            kr = clean_ko(kr_raw)
            if not jp or not kr:
                continue
            exact[jp][kr] += 1
            if len(jp) <= 25:
                short.append((jp, kr, jp_raw, kr_raw))
    return exact, short


def load_ec_pairs():
    pairs = []
    for path in sorted(glob.glob(os.path.join(GT, "gt_input", "*.json"))):
        base = os.path.basename(path)
        out_path = os.path.join(GT, "gt_output", base)
        if not os.path.exists(out_path):
            continue
        with open(path, encoding="utf-8") as f:
            ja_items = json.load(f)
        with open(out_path, encoding="utf-8") as f:
            ko_items = json.load(f)
        for i, item in enumerate(ja_items):
            ja = (item.get("message") or "").strip()
            ko = (ko_items[i].get("message") or "").strip() if i < len(ko_items) else ""
            if ja and ko:
                pairs.append((ja, ko))
    return pairs


# ---------------------------------------------------------------- 표기 추론

def span_forms(ko_lines, gc, total):
    """한국어 줄들에서 후보 용어에 해당할 수 있는 표기 후보들을 만든다.

    1토큰 후보 중 등장 비율이 가장 높은 것을 기준으로 잡고, 그 토큰을 포함하면서
    비율이 기준의 60% 이상인 더 긴 구를 후보에 더한다.
    반환: (forms, base) — forms 는 (coverage, lift, n_tokens, 구문자열) 목록
    """
    if not ko_lines or not total:
        return [], None
    cnt = collections.Counter()
    for ko in ko_lines:
        for g in grams(ko):
            cnt[g] += 1
    n = len(ko_lines)
    valid = []
    for g, c in cnt.items():
        cov = c / n
        gcov = gc.get(g, 0) / total
        lift = (cov / gcov) if gcov else 99.0
        toks = g.split(" ")
        if any(t in HONORIFIC for t in toks):
            continue
        if any(t in STOP_TOK for t in toks):
            continue
        if len(g) <= 1:
            if cov < 0.4 or lift < 6:
                continue
        else:
            if cov < 0.12 or lift < 3:
                continue
        valid.append((cov, lift, len(toks), g))
    if not valid:
        return [], None
    one = [v for v in valid if v[2] == 1]
    if one:
        base = max(one, key=lambda v: (v[0], v[1]))
        forms = [base]
        forms += [
            v
            for v in valid
            if v[2] > 1 and base[3] in v[3].split(" ") and v[0] >= 0.6 * base[0]
        ]
    else:
        base = max(valid, key=lambda v: (v[2], v[0]))
        forms = [base]
    return forms, base


def tok_f1(form: str, prior: str) -> float:
    a = [t for t in stems(form) if len(t) >= 1]
    b = [t for t in stems(prior) if len(t) >= 1]
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    if inter:
        p = inter / len(sa)
        r = inter / len(sb)
        return 2 * p * r / (p + r)
    na, nb = "".join(a), "".join(b)
    pre = 0
    for x, y in zip(na, nb):
        if x == y:
            pre += 1
        else:
            break
    return 0.2 + pre * 0.01 if pre >= 2 else 0.0


def choose_form(forms, prior):
    if not forms:
        return None
    if prior:
        return max(forms, key=lambda v: (round(tok_f1(v[3], prior), 6), v[2], v[0]))
    return max(forms, key=lambda v: (v[2], v[0]))


def similar(a: str, b: str) -> bool:
    """공식 표기와 EC 현재 표기가 같은 개체로 볼 만큼 닮았는지(가타카나 오탐 거르기)."""
    A, B = normko(a), normko(b)
    if not A or not B:
        return False
    if A in B or B in A:
        return True
    ta = {t for t in stems(a) if len(t) >= 2}
    tb = {t for t in stems(b) if len(t) >= 2}
    if ta & tb:
        return True
    pre = 0
    for x, y in zip(A, B):
        if x == y:
            pre += 1
        else:
            break
    return pre >= 2


def quote_evidence(rows, term):
    found = []
    for jp, kr, jp_raw, kr_raw in rows:
        contents = [clean_jp(m.group(1)) for m in JP_QUOTE_RE.finditer(jp_raw)]
        if term not in contents:
            continue
        spans = [clean_ko(m.group(1)) for m in KO_QUOTE_RE.finditer(kr_raw)]
        spans = [s for s in spans if s]
        if not spans:
            continue
        spans.sort(key=len)
        found.append((spans[0], jp, kr))
    if not found:
        return None
    c = collections.Counter(x[0] for x in found)
    ko = c.most_common(1)[0][0]
    cov = c[ko] / len(rows)
    ex = [(jp, kr) for k, jp, kr in found if k == ko][:2]
    return {"ko": ko, "cov": cov, "lift": 99.0, "method": "quote", "examples": ex}


def prior_span(prior, ko_lines):
    """EC 현재 표기가 리버스 번역문에도 충분히(50% 이상) 그대로 쓰이면 그 표기를 쓴다.

    예: 目的(목적)은 리버스에서 대부분 目的地(목적지)로 나오므로 '목적'만 잘라 쓴다.
    魔晄(마코)처럼 리버스가 전혀 다른 표기(마황)를 쓰면 이 경로로는 잡히지 않는다.
    """
    if not prior or not ko_lines:
        return None
    raw = [t for t in KO_SEP.split(prior) if t]
    if len(raw) != 1:
        return None
    ps = [t for t in stems(prior) if len(t) >= 2]
    if len(ps) != 1:
        return None
    p = ps[0]
    hit = 0
    for ko in ko_lines:
        if any(t.startswith(p) for t in stems(ko)):
            hit += 1
    if hit >= 0.5 * len(ko_lines):
        return p, hit / len(ko_lines)
    return None


def partial_evidence(rows, term, gc, total, prior=""):
    q = quote_evidence(rows, term)
    if q:
        return q
    if len(rows) < 2:
        return None
    ko_lines = [kr for _, kr, _, _ in rows]
    ps = prior_span(prior, ko_lines) if prior else None
    if ps:
        g, cov = ps
        ex = [
            (jp, kr)
            for jp, kr, _, _ in rows
            if any(t.startswith(g) for t in stems(kr))
        ][:2]
        return {"ko": g, "cov": cov, "lift": 99.0, "method": "prior", "examples": ex}
    forms, base = span_forms(ko_lines, gc, total)
    if not allow_ext(term):
        forms = [base] if base else []
    p = choose_form(forms, prior)
    if not p:
        return None
    cov, lift, _, g = p
    ex = [(jp, kr) for jp, kr, _, _ in rows if g in kr][:2]
    if not ex:
        ex = [(jp, kr) for jp, kr, _, _ in rows][:2]
    return {"ko": g, "cov": cov, "lift": lift, "method": "ngram", "examples": ex}


def find_official(term, exact, short, gc, total, prior=""):
    c = exact.get(term)
    if c:
        ko = c.most_common(1)[0][0]
        return {
            "ko": ko,
            "evidence": "exact",
            "examples": [(term, ko)],
            "cov": 1.0,
            "lift": 99.0,
            "method": "exact",
        }
    rows = [t for t in short if term in t[0] and occurrence_ok(t[0], term)]
    if rows:
        p = partial_evidence(rows, term, gc, total, prior)
        if p:
            bad = False
            # 가타카나 단어가 다른 단어의 일부로 걸린 경우(バカ/バカンス)를 거른다.
            if p["method"] != "quote" and is_kana_only(term) and prior and not similar(p["ko"], prior):
                bad = True
            if not any("가" <= ch <= "힣" for ch in p["ko"]):
                bad = True
            if not bad:
                return {
                    "ko": p["ko"],
                    "evidence": "partial",
                    "examples": p["examples"],
                    "cov": p["cov"],
                    "lift": p["lift"],
                    "method": p["method"],
                }
    return {
        "ko": "",
        "evidence": "not_found",
        "examples": [],
        "cov": 0.0,
        "lift": 0.0,
        "method": "",
    }


def cmp_key(s: str) -> str:
    """표기 비교용 키. 조사/어미와 띄어쓰기 차이는 같은 표기로 본다."""
    return "".join(stems(s))


def normko(s: str) -> str:
    s = re.sub(r"[\s　・·.'’]+", "", s or "")
    return s.lower()


def map_name(source: str, ko: str, ko2ja):
    """화자 영어명의 EC 한국어 표기를 이용해 일본어 원어 후보를 찾는다."""
    key = normko(ko)
    if not key or not any("가" <= ch <= "힣" for ch in key):
        return ""
    best = None
    for k, lst in ko2ja.items():
        if k == key:
            pass
        elif key.startswith(k):
            rest = key[len(k) :]
            if not (len(rest) <= 1 or re.fullmatch(r"[ivx0-9]+", rest)):
                continue
        else:
            continue
        for freq, ja in lst:
            score = (freq, len(k))
            if best is None or score > best[0]:
                best = (score, ja)
    if not best:
        return ""
    ja = best[1]
    m = re.search(r"([IVX]{2,}|\d+)$", source or "")
    if m and m.group(1) not in ja:
        ja += m.group(1)
    return ja


def ec_current(term, table_ko, ec_pairs, ec_gc):
    lines = [ko for ja, ko in ec_pairs if term in ja and occurrence_ok(ja, term)]
    forms, _ = span_forms(lines, ec_gc, len(ec_pairs)) if lines else ([], None)
    if not allow_ext(term):
        return table_ko or (forms[0][3] if forms else "")
    if not forms:
        return table_ko
    best = max(forms, key=lambda v: (v[2], v[0]))
    if best[0] >= 0.35:
        return best[3]
    return table_ko or best[3]


# ---------------------------------------------------------------- 본체

def main():
    exact, short = load_rebirth()
    gc = collections.Counter()
    for jp, kr, _, _ in short:
        for g in grams(kr):
            gc[g] += 1
    total = len(short)

    ec_pairs = load_ec_pairs()
    ec_gc = collections.Counter()
    for ja, ko in ec_pairs:
        for g in grams(ko):
            ec_gc[g] += 1

    kat_rows = load_tsv("ec_terms_katakana.tsv")
    kan_rows = load_tsv("ec_terms_kanji.tsv")
    quo_rows = load_tsv("ec_terms_quoted.tsv")
    nam_rows = load_tsv("ec_terms_names.tsv")

    # 이름(영어) -> 일본어 후보 인덱스
    ko2ja = collections.defaultdict(list)
    for r in kat_rows:
        if r.get("kind") in ("filler", "pronoun"):
            continue
        key = normko(top_variant(r.get("ko_variants", "")))
        if key:
            ko2ja[key].append((int(r.get("freq") or 0), r["term"]))
    for r in kan_rows:
        key = normko(top_variant(r.get("ko_variants", "")))
        if key:
            ko2ja[key].append((int(r.get("freq") or 0), r["term"]))

    records = []
    considered = {"katakana": 0, "kanji": 0, "quoted": 0, "names": 0}
    adopted = {"katakana": 0, "kanji": 0, "quoted": 0, "names": 0}

    def make(ja, kind, freq, ko_current, from_ec=True):
        if from_ec:
            ko_current = ec_current(ja, ko_current, ec_pairs, ec_gc)
        ev = find_official(ja, exact, short, gc, total, prior=ko_current)
        official = ev["ko"]
        status = "not_found"
        if official and ko_current:
            status = "same" if cmp_key(official) == cmp_key(ko_current) else "diff"
        ex = " || ".join(
            f"{a}=>{b}".replace("\t", " ").replace("\n", " ").replace("\\n", " / ")[:120]
            for a, b in ev["examples"]
        )
        rec = {
            "ja": ja,
            "ko_official": official,
            "evidence": ev["evidence"],
            "example": ex,
            "ko_current": ko_current,
            "ec_freq": freq,
            "status": status,
            "_kind": kind,
            "_cov": ev["cov"],
            "_lift": ev["lift"],
            "_method": ev["method"],
        }
        return rec, ev

    def add(ja, kind, freq, ko_current, from_ec=True):
        rec, _ = make(ja, kind, freq, ko_current, from_ec)
        records.append(rec)

    for r in kat_rows:
        if r.get("kind") in ("filler", "pronoun"):
            continue
        considered["katakana"] += 1
        add(r["term"], "katakana", int(r.get("freq") or 0),
            top_variant(r.get("ko_variants", "")))
        adopted["katakana"] += 1

    for r in kan_rows:
        considered["kanji"] += 1
        term = r["term"]
        rec, ev = make(term, "kanji", int(r.get("freq") or 0),
                       top_variant(r.get("ko_variants", "")))
        if ev["evidence"] == "not_found":
            continue
        if ev["evidence"] == "partial" and ev["method"] != "quote":
            span = ev["ko"].replace(" ", "")
            need = 1 if len(term) == 1 else 2
            min_cov = 0.40 if (r.get("in_dict") or "").strip() else 0.45
            if len(span) < need or ev["cov"] < min_cov or ev["lift"] < 5:
                continue
        if not any("가" <= ch <= "힣" for ch in ev["ko"]):
            continue
        # 사전에 없는 일반 한자어는, 리버스 표기가 EC 현재 표기와 전혀 닮지 않으면
        # 맥락어를 잘못 집은 것으로 보고 버린다(仕業→몬스터, 苦手→클라우드 등).
        if (
            ev["evidence"] == "partial"
            and ev["method"] != "quote"
            and not (r.get("in_dict") or "").strip()
            and not similar(ev["ko"], rec["ko_current"])
        ):
            continue
        records.append(rec)
        adopted["kanji"] += 1

    for r in quo_rows:
        considered["quoted"] += 1
        add(r["term"], "quoted", int(r.get("freq") or 0),
            top_variant(r.get("ko_variants", "")))
        adopted["quoted"] += 1

    for r in nam_rows:
        considered["names"] += 1
        source = r.get("source_name") or ""
        ko = top_variant(r.get("ko_variants", ""))
        ja = map_name(source, ko, ko2ja) or source
        add(ja, "names", int(r.get("freq") or 0), ko, from_ec=False)
        adopted["names"] += 1

    # 같은 일본어 키가 여러 표에서 나오면 빈도가 큰 쪽만 남긴다.
    dedup = {}
    for rec in records:
        key = rec["ja"]
        if key not in dedup or rec["ec_freq"] > dedup[key]["ec_freq"]:
            dedup[key] = rec
    final = sorted(dedup.values(), key=lambda r: (-r["ec_freq"], r["ja"]))

    cols = ["ja", "ko_official", "evidence", "example", "ko_current", "ec_freq", "status"]
    with open(OUT_DRAFT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t", quoting=csv.QUOTE_NONE)
        w.writeheader()
        for rec in final:
            w.writerow({c: str(rec[c]).replace("\t", " ") for c in cols})

    diff = [r for r in final if r["status"] == "diff"]
    with open(OUT_DIFF, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t", quoting=csv.QUOTE_NONE)
        w.writeheader()
        for rec in diff:
            w.writerow({c: str(rec[c]).replace("\t", " ") for c in cols})

    # ------------------------------------------------------------ 보고
    ev_count = collections.Counter(r["evidence"] for r in final)
    st_count = collections.Counter(r["status"] for r in final)
    print(f"rebirth rows: exact keys={len(exact)}, short<=25={total}")
    print(f"EC pairs: {len(ec_pairs)}")
    print(f"후보(원본): {considered}  합계={sum(considered.values())}")
    print(f"채택(출력): {adopted}  합계={sum(adopted.values())}")
    print(f"중복 제거 후: {len(final)}")
    print(f"evidence: {dict(ev_count)}")
    print(f"status:   {dict(st_count)}")
    print(f"draft: {OUT_DRAFT}")
    print(f"diff : {OUT_DIFF} ({len(diff)} rows)")

    checks = [
        ("ツォン", "청"),
        ("タークス", "턱스"),
        ("魔晄", "마황"),
        ("魔晄炉", "마황로"),
        ("ケット・シー", "캐트시"),
        ("ルーファウス", "루퍼스"),
        ("ライフストリーム", "라이프 스트림"),
        ("リユニオン", "리유니온"),
        ("死の宣告", "죽음의 선고"),
        ("元ソルジャー", "전직 솔저"),
        ("ウォール・マーケット", "월 마켓"),
        ("ゴールドソーサー", "골드 소서"),
    ]
    print("기준값 확인:")
    npass = 0
    for ja, want in checks:
        ev = find_official(ja, exact, short, gc, total)
        ok = ev["ko"] == want
        npass += 1 if ok else 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {ja} -> {ev['ko'] or '(none)'}"
              f"  (want {want}, {ev['evidence']}/{ev['method']})")
    print(f"기준값: {npass}/{len(checks)}")


if __name__ == "__main__":
    main()
