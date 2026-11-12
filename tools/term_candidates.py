#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FF7 에버크라이시스 스토리 원문(일본어)에서 용어집 후보를 뽑고,
현재 한국어 번역에서의 대응 표기 변형을 함께 집계한다.

입력 (읽기 전용):
  gt_project/gt_input/*.json   [{"name": 화자, "message": 일본어}, ...]
  gt_project/gt_output/*.json  같은 이름/같은 순서, message 가 한국어
  gt_project/Dict/gpt_dict.txt 영어(또는 일본어)키 <TAB> 한국어 <TAB> 메모

출력:
  work/glossary/ec_terms_katakana.tsv
  work/glossary/ec_terms_names.tsv
  work/glossary/ec_terms_kanji.tsv
  work/glossary/ec_terms_quoted.tsv   (「」『』 안의 짧은 명사구)
  work/glossary/ec_terms_rare.tsv     (빈도 3 미만)
  work/glossary/old_dict_hits.tsv     (기존 용어집 항목별 원문/번역 매칭 횟수)

사용:
  python tools/term_candidates.py [--root 프로젝트루트]
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

# ---------------------------------------------------------------- 정규식

# 가타카나 연속(장음 ー, 중점 ・, 반복기호 ヽヾ, 반각 가타카나 포함)
KATA_RUN = re.compile(r"[ァ-ヺーヽヾｦ-ﾟ・]+")
KATA_LETTER = re.compile(r"[ァ-ヺヽヾｦ-ﾟ]")
# 한자 연속
KANJI_RUN = re.compile(r"[一-鿿]+")
# 「」『』 안의 짧은 구
QUOTED = re.compile(r"[「『]([^「」『』\n]{1,20})[」』]")
# 한국어 토큰
KO_TOKEN = re.compile(r"[가-힣]+")  # 1글자 표기(츤, 맷, 별)도 잡는다

# ---------------------------------------------------------------- 사전

# 가타카나 후보 중 고유명사가 아닌 것(대명사/지시어/감탄/의성어) 표시용.
# 파일에서 지우지는 않고 kind 컬럼으로 구분한다.
KATA_PRONOUN = {
    "オレ", "オレたち", "オレら", "オマエ", "オマエら", "オメエ", "アンタ", "アンタたち",
    "アンタら", "キミ", "キミたち", "キサマ", "テメエ", "テメー", "ワタシ", "ワタシたち",
    "ボク", "ボクら", "アタシ", "ワシ", "オイラ", "ワレ", "ワレワレ", "コイツ", "ソイツ",
    "アイツ", "コイツら", "アイツら", "コレ", "ソレ", "アレ", "ドレ", "コレら", "ココ",
    "ソコ", "アソコ", "ドコ", "コッチ", "ソッチ", "アッチ", "ドッチ", "コチラ", "ソチラ",
    "アチラ", "ドチラ", "モノ", "コト", "トコロ", "ヤツ", "ヤツら", "ナニ", "ダレ",
    "ドウシテ", "ナゼ", "イツ", "ドウ", "モウ", "マダ", "ゼンゼン", "スゴイ", "ハイ",
    "イエ", "イイエ", "ウン", "ウウン", "エエ", "アア", "オオ", "ハイハイ", "アンタたち",
}

KATA_FILLER = {
    "ハハ", "ハハハ", "ハハハハ", "ハハハハハ", "フフ", "フフフ", "フフフフ", "アハ",
    "アハハ", "アハハハ", "ウフフ", "クク", "クスクス", "エヘ", "エヘヘ", "ホホ", "ホホホ",
    "ハァ", "ハア", "ハアハア", "フウ", "フー", "ヘエ", "ヘー", "ホウ", "ホー", "ヒュウ",
    "ドキ", "ドキドキ", "ワクワク", "バタバタ", "ゴゴゴ", "ズズ", "ガタ", "ゴト", "パタ",
    "ピタ", "ドン", "バン", "ガン", "ズドン", "ビュン", "シュッ", "ザッ", "ジャ", "ジャン",
    "チュン", "ピピ", "ピー", "ブー", "ウー", "ウンウン", "ウウ", "アッ", "ハッ", "フッ",
    "ン", "ンン", "フン", "フフン", "ニヤ", "ニコ", "ギク", "ハラハラ", "ソワソワ",
    "ウロウロ", "ブラブラ", "ゴホ", "ゴホン", "コホン", "ゼエ", "ゼェ", "アアア", "ウウウ",
    "オオオ", "ハハッ", "ウフ", "クス", "グス", "エーン", "ワア", "ワー", "キャア", "キャー",
    "ウワ", "ウワア", "ヒイ", "ヒィ", "オイ", "オイオイ", "ホラ", "ソラ", "ヨシ", "ヨーシ",
    "ドサ", "ドサッ", "バタン", "ガシャ", "ガチャ", "ピシャ", "バシャ", "ジャジャ", "ズガ",
    "ゴオ", "ゴォ", "ブオ", "ブォ", "ヒュー", "ピュウ", "ビュウ", "ザワ", "ザワザワ",
    "ゴクリ", "クッ", "グッ", "ギリ", "ギリギリ", "ビク", "ビクビク", "プル", "ブル",
    "ブルブル", "カチ", "カチカチ", "チラ", "チラリ", "ジロ", "ジロリ", "ジッ", "ジー",
    "ニャ", "ニャー", "ニャン", "ニャア", "ニャンコ", "ワン", "ワオ", "キャッ", "キャッキャ",
    "クン", "クンクン", "フガ", "フガフガ", "ピシ", "ピシピシ", "バキ", "バキバキ",
    "メキ", "メキメキ", "ズバ", "ズバッ", "ガツ", "ガツガツ", "バリ", "バリバリ",
}

# 가타카나 문맥의 반복 패턴(ドキドキ / ハハハ 등)을 감탄/의성어로 간주하기 위한 길이
REPEAT_MAX_UNIT = 3

# 한자 후보로 반드시 넣을 고유명사 시드(부분 문자열로도 집계)
KANJI_SEEDS = [
    "魔晄", "神羅", "古代種", "星", "セトラ", "ウェポン", "ジェノバ", "ライフストリーム",
    "約束の地", "五台", "ウータイ", "コスモキャニオン", "ゴンガガ", "ニブルヘイム",
    "ミッドガル", "ジュノン", "ゴールドソーサー", "竜巻", "黒マテリア", "白マテリア",
]

# 한국어 조사/어미(긴 것부터)
KO_PARTICLES = sorted(
    [
        "이었다면", "이었다", "이었어", "였어", "이었", "였", "이었다가", "에서는",
        "에게서", "에게는", "한테는", "으로는", "라고는", "이라는", "라는", "입니다",
        "이에요", "예요", "이야", "이죠", "이랑은", "이랑", "랑", "이고", "라고",
        # 명사 뒤에 붙는 서술/연결 어미(표기 변형 비교를 위해 떼어 낸다)
        "이었습니다", "이지만", "이라면", "이라서", "이라니", "이라고", "이라도",
        "이나마", "이든지", "이든", "이구나", "이군", "이네", "이니까", "이야말로",
        "에서는", "에서도", "에게도", "한테도", "까지도", "부터는", "으로도",
        "로서", "로써", "로는", "라면", "라도", "래", "냐", "니까", "는데", "은데",
        "잖아", "더라", "더니", "구나", "까", "죠", "니", "다", "야", "들",
        "에서", "에게", "한테", "께서", "으로", "로", "과", "와", "을", "를", "은",
        "는", "이", "가", "의", "에", "도", "만", "보다", "부터", "까지", "처럼",
        "마저", "조차", "밖에", "이나", "든지", "든가",
    ],
    key=len,
    reverse=True,
)

KO_STOP = {
    "있다", "없다", "하다", "되다", "같다", "싶다", "않다", "모르다", "알다", "오다",
    "가다", "보다", "주다", "받다", "만들다", "나오다", "들어", "이거", "그거", "저거",
    "이것", "그것", "저것", "여기", "거기", "저기", "우리", "너희", "당신", "자신",
    "사람", "녀석", "놈", "것", "거", "게", "수", "때", "줄", "데", "중", "더", "또",
    "잘", "안", "못", "왜", "뭐", "누구", "어디", "언제", "지금", "정말", "진짜",
    "아주", "너무", "모두", "전부", "다시", "아직", "이미", "계속", "먼저", "나중",
    "그냥", "조금", "많이", "하나", "둘", "이런", "그런", "저런", "어떤", "무슨",
    "그래", "그러나", "하지만", "그리고", "그래서", "그런데", "근데", "그럼", "그러면",
    "아니", "응", "어", "음", "아", "오", "와", "하하", "허허", "이제", "그게", "이게",
    "저게", "무엇", "어떻게", "그렇게", "이렇게", "저렇게", "같은", "그것도", "이건",
    "그건", "저건", "내가", "네가", "제가", "그녀", "그놈", "이놈", "저놈", "당장",
    # 조사 제거 뒤 1글자로 남는 흔한 문법어(변형 후보에서 제외)
    "나", "너", "저", "그", "이", "것", "수", "때", "거", "게", "데", "줄", "중", "등",
    "및", "또", "더", "잘", "못", "안", "왜", "뭐", "좀", "날", "널", "절", "걔", "쟤",
    "만", "듯", "양", "쪽", "편", "번", "층", "개", "명", "년", "월", "분", "초", "원",
    "살", "번째", "내", "네", "제", "야", "요", "함", "듯이",
    # 1글자 토큰으로 흔히 나오는 기능어
    "난", "널", "절", "걸", "겁", "뭐", "좀", "잘", "못", "안", "왜", "또", "더", "다",
    "니", "쯤", "뿐", "척", "채", "밖", "전", "후", "웬", "왠", "얼", "몇", "온", "땐",
    "군", "냥", "랑", "줘", "봐", "줄", "줌", "줍", "죠", "죵", "용", "임", "님",
}


RAW_COUNTS = collections.Counter()   # 조사 제거 전 원형 빈도
_NORM_CACHE = {}


def _stem_productive(stem: str, suf: str) -> bool:
    """어간이 조사 하나에만 붙는지, 여러 조사와 두루 결합하는지 판별한다."""
    if RAW_COUNTS.get(stem, 0) >= 2:
        return True
    for p in KO_PARTICLES:
        if p.startswith(suf):
            continue      # 같은 계열(이 / 이야)은 어간의 증거로 보지 않는다
        if RAW_COUNTS.get(stem + p, 0) >= 2:
            return True
    return False


def norm_ko(token: str) -> str:
    """한국어 토큰에서 조사/어미를 떼어 표기 변형을 비교 가능하게 만든다.

    1글자 조사는 어간이 1글자로 남아도 떼어 낸다(예: 별을 → 별, 츤이 → 츤).
    그래야 星 / ツォン 같은 짧은 표기의 대응을 잡을 수 있다.
    """
    cached = _NORM_CACHE.get(token)
    if cached is not None:
        return cached
    out = token
    for suf in KO_PARTICLES:
        if token.endswith(suf):
            stem = token[: len(token) - len(suf)]
            if len(stem) >= (1 if len(suf) == 1 else 2):
                out = stem
                break
    if out != token:
        # 어간이 다른 조사와도 두루 결합하면 진짜 어간이므로 떼고,
        # 이 조사 하나에만 붙어 있다면 조사가 아니라 어휘의 일부다(예: 우타이).
        if not _stem_productive(out, suf):
            out = token
    _NORM_CACHE[token] = out
    return out


def is_repeat_noise(word: str) -> bool:
    """ドキドキ / ハハハ 처럼 짧은 단위의 반복으로만 된 가타카나를 판별."""
    body = word.replace("・", "")
    if len(body) < 2:
        return True
    for unit in range(1, REPEAT_MAX_UNIT + 1):
        if len(body) % unit == 0 and len(body) // unit >= 2:
            if body[:unit] * (len(body) // unit) == body:
                return True
    return False


def kata_kind(word: str) -> str:
    if word in KATA_PRONOUN:
        return "pronoun"
    if word in KATA_FILLER or is_repeat_noise(word):
        return "filler"
    return "term"


# ---------------------------------------------------------------- 로딩


def load_corpus(root: str):
    """(파일명, 항목 인덱스, 화자, 일본어, 한국어) 목록과 파일 수를 돌려준다."""
    in_dir = os.path.join(root, "gt_project", "gt_input")
    out_dir = os.path.join(root, "gt_project", "gt_output")
    files = sorted(glob.glob(os.path.join(in_dir, "*.json")))
    records = []
    missing_out = []
    file_count = 0
    for path in files:
        base = os.path.basename(path)
        out_path = os.path.join(out_dir, base)
        with open(path, encoding="utf-8") as fh:
            ja_items = json.load(fh)
        if os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as fh:
                ko_items = json.load(fh)
        else:
            ko_items = []
            missing_out.append(base)
        file_count += 1
        for idx, item in enumerate(ja_items):
            ja = (item.get("message") or "").strip()
            name = (item.get("name") or "").strip()
            ko = ""
            ko_name = ""
            if idx < len(ko_items):
                ko = (ko_items[idx].get("message") or "").strip()
                ko_name = (ko_items[idx].get("name") or "").strip()
            records.append((base, idx, name, ja, ko, ko_name))
    return records, file_count, missing_out


def load_dict(root: str):
    path = os.path.join(root, "gt_project", "Dict", "gpt_dict.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines()
    entries = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        key = parts[0].strip()
        ko = parts[1].strip() if len(parts) > 1 else ""
        memo = parts[2].strip() if len(parts) > 2 else ""
        if key:
            entries.append((key, ko, memo))
    return entries


# ---------------------------------------------------------------- 집계


def coverage_variants(indices, ko_lines, ko_tokens, global_counts, global_total, topn=3):
    """후보가 나온 줄들의 번역문에서, 그 줄들에만 유난히 몰려 있는 한국어 명사를 찾는다.

    점수는 (부분집합 내 비율) / (전체 비율) = lift. 빈도와 등장 줄 비율을 함께 본다.
    """
    # 같은 줄에 두 번 나온 경우를 한 줄로 센다(등장 줄 비율의 분모)
    indices = sorted(set(indices))
    n = len(indices)
    if not n or not global_total:
        return [], []
    sub = collections.Counter()
    sub_lines = collections.Counter()
    tok_lines = collections.defaultdict(set)
    sub_total = 0
    for i in indices:
        seen = set()
        for tok in ko_tokens[i]:
            sub[tok] += 1
            sub_total += 1
            if tok not in seen:
                sub_lines[tok] += 1
                tok_lines[tok].add(i)
                seen.add(tok)
    if not sub_total:
        return [], []
    cands = []
    for tok, c in sub.items():
        if c < 2 or tok in KO_STOP:
            continue
        cov = sub_lines[tok] / n
        g = global_counts.get(tok, 0)
        lift = (c / sub_total) / (g / global_total) if g else 99.0
        if len(tok) == 1 and (cov < 0.4 or lift < 6.0):
            continue
        if cov >= 0.12 and (lift >= 3.0 or cov >= 0.35):
            # 상위 후보 안에서 다른 후보의 부분 문자열이면 접는다(예: 마코 / 마코로)
            cands.append((tok, c, cov, lift))
    cands.sort(key=lambda x: (-x[2], -x[1]))
    kept = []
    for tok, c, cov, lift in cands:
        # 앞서 뽑힌 표기의 부분 문자열이거나, 앞서 뽑힌 표기를 포함하는 확장형이면
        # 같은 표기의 어형 변화로 보고 접는다(예: 마코 / 마코로, 팀 / 팀으).
        if any(same_stem(tok, k[0]) for k in kept):
            continue
        # 같은 줄에 거의 항상 함께 나오는 말은 다른 개체일 뿐 표기 변형이 아니다.
        # (예: チャキヤ 줄에 같이 나오는 '오르타')
        lines = tok_lines[tok]
        if any(
            len(lines & tok_lines[k[0]]) >= 0.5 * min(len(lines), len(tok_lines[k[0]]))
            for k in kept
        ):
            continue
        kept.append((tok, c, cov, lift))
        if len(kept) >= topn:
            break
    return kept, cands


def fmt_variants(variants):
    return "; ".join(f"{t}({c},{cov*100:.0f}%)" for t, c, cov, _ in variants)


def split_flag(variants):
    """번역이 실질적으로 둘 이상으로 갈라졌는지."""
    if len(variants) < 2:
        return 0
    strong = [v for v in variants if v[1] >= 3 and v[2] >= 0.2]
    if len(strong) < 2:
        return 0
    return 1 if variants[0][2] < 0.85 else 0


# 표기 뒤에 붙는 문법 형태소(이것만 붙으면 같은 표기의 어형 변화로 본다)
KO_EXT_SUFFIXES = {
    "으", "다", "인", "들", "은", "는", "을", "를", "의", "에", "로", "과", "와", "도",
    "만", "엔", "란", "냐", "죠", "요", "임", "면", "서", "이", "가", "야", "람", "쯤",
    "채", "척", "듯", "뿐", "밖", "조차", "마저", "처럼", "보다", "부터", "까지", "만큼",
    "이나", "든지", "든가", "이다", "인가", "이며", "이고", "인데", "는데", "은데", "이랑",
    "랑", "이에요", "예요", "입니다", "이죠", "이야", "이었", "였", "이라는", "라는",
}


def same_stem(a: str, b: str) -> bool:
    """두 한국어 표기가 어형 변화 관계인지(한쪽이 다른 쪽 + 문법 형태소)."""
    if a == b:
        return True
    if a.startswith(b) and a[len(b):] in KO_EXT_SUFFIXES:
        return True
    if b.startswith(a) and b[len(a):] in KO_EXT_SUFFIXES:
        return True
    return False


def write_tsv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(header) + "\n")
        for row in rows:
            fh.write("\t".join(str(x) for x in row) + "\n")
    return len(rows)


def clip(text: str, limit: int = 80) -> str:
    text = text.replace("\r", " ").replace("\n", " / ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------------------------------------------------------------- 본체


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    root = args.root
    out_dir = os.path.join(root, "work", "glossary")

    records, file_count, missing_out = load_corpus(root)
    dict_entries = load_dict(root)
    ja_keys = {k for k, _, _ in dict_entries if re.search(r"[぀-ヿ一-鿿]", k)}

    # 줄 단위 자료
    ja_lines = [r[3] for r in records]
    ko_lines = [r[4] for r in records]
    ja_text = "\n".join(ja_lines)
    ko_text = "\n".join(ko_lines)

    for line in ko_lines:
        RAW_COUNTS.update(KO_TOKEN.findall(line))

    ko_tokens = []
    global_counts = collections.Counter()
    for line in ko_lines:
        toks = [norm_ko(t) for t in KO_TOKEN.findall(line)]
        toks = [t for t in toks if len(t) >= 1 and t not in KO_STOP]
        ko_tokens.append(toks)
        global_counts.update(toks)
    global_total = sum(global_counts.values()) or 1

    # --- 후보 수집 -------------------------------------------------
    kata = collections.OrderedDict()          # term -> dict
    kanji = collections.OrderedDict()
    quoted = collections.OrderedDict()
    name_stat = collections.OrderedDict()
    kata_indices = collections.defaultdict(list)
    kanji_indices = collections.defaultdict(list)
    quoted_indices = collections.defaultdict(list)
    name_indices = collections.defaultdict(list)
    name_ko = collections.defaultdict(collections.Counter)

    for i, rec in enumerate(records):
        base, idx, name, ja, ko, ko_name = rec
        if not ja:
            pass
        # (b) 화자 이름
        if name:
            st = name_stat.setdefault(name, {"freq": 0, "files": set()})
            st["freq"] += 1
            st["files"].add(base)
            name_indices[name].append(i)
            if ko_name:
                name_ko[name][ko_name] += 1
        if not ja:
            continue
        # (a) 가타카나 연속어
        for m in KATA_RUN.finditer(ja):
            w = m.group().strip("・")
            if not w:
                continue
            if len(KATA_LETTER.findall(w)) < 2:
                continue
            st = kata.setdefault(w, {"freq": 0, "files": set(), "example": None, "ex_ko": None})
            st["freq"] += 1
            st["files"].add(base)
            if st["example"] is None:
                st["example"], st["ex_ko"] = ja, ko
            kata_indices[w].append(i)
        # (c) 「」『』 안의 짧은 구
        for m in QUOTED.finditer(ja):
            w = m.group(1).strip()
            if not 2 <= len(w) <= 10:
                continue
            if not re.search(r"[぀-ヿ一-鿿]", w):
                continue
            st = quoted.setdefault(w, {"freq": 0, "files": set(), "example": None, "ex_ko": None})
            st["freq"] += 1
            st["files"].add(base)
            if st["example"] is None:
                st["example"], st["ex_ko"] = ja, ko
            quoted_indices[w].append(i)
        # (d) 한자 연속 2~4자
        for m in KANJI_RUN.finditer(ja):
            w = m.group()
            if not 2 <= len(w) <= 4:
                continue
            st = kanji.setdefault(w, {"freq": 0, "files": set(), "example": None, "ex_ko": None})
            st["freq"] += 1
            st["files"].add(base)
            if st["example"] is None:
                st["example"], st["ex_ko"] = ja, ko
            kanji_indices[w].append(i)

    # --- 표 만들기 -------------------------------------------------
    def build(store, indices, kind_fn=None, extra_fn=None):
        rows = []
        for term, st in store.items():
            vars_, _all = coverage_variants(
                indices.get(term, []), ko_lines, ko_tokens, global_counts, global_total
            )
            substr = ja_text.count(term)
            if term in ja_keys:
                in_dict = "exact"
            elif any(k in term for k in ja_keys):
                in_dict = "partial"
            else:
                in_dict = ""
            row = [
                term,
                kind_fn(term) if kind_fn else "",
                st["freq"],
                len(st["files"]),
                substr,
                in_dict,
                fmt_variants(vars_),
                split_flag(vars_),
                clip(st["example"] or ""),
                clip(st["ex_ko"] or ""),
            ]
            if extra_fn:
                row = extra_fn(term, st, vars_) + row
            rows.append((st["freq"], len(st["files"]), term, row))
        rows.sort(key=lambda x: (-x[0], -x[1], x[2]))
        return [r[3] for r in rows]

    KATA_HEADER = [
        "term", "kind", "freq", "files", "substr_freq", "in_dict",
        "ko_variants", "split", "example_ja", "example_ko",
    ]
    all_kata = build(kata, kata_indices, kind_fn=kata_kind)
    kata_main = [r for r in all_kata if r[2] >= 3]
    kata_rare = [r for r in all_kata if r[2] < 3]

    all_kanji = build(kanji, kanji_indices)
    # 시드 한자어는 부분 문자열 집계 행을 별도로 덧붙인다.
    kanji_terms = {r[0] for r in all_kanji}
    seed_rows = []
    for seed in KANJI_SEEDS:
        if not re.search(r"[一-鿿]", seed):
            continue
        c = ja_text.count(seed)
        if c == 0 or seed in kanji_terms:
            continue
        vars_, _ = coverage_variants(
            [i for i, l in enumerate(ja_lines) if seed in l],
            ko_lines, ko_tokens, global_counts, global_total,
        )
        seed_rows.append([
            seed, "seed", c, len({records[i][0] for i, l in enumerate(ja_lines) if seed in l}),
            c, "exact" if seed in ja_keys else ("partial" if any(k in seed for k in ja_keys) else ""),
            fmt_variants(vars_), split_flag(vars_),
            clip(next((l for l in ja_lines if seed in l), "")),
            clip(next((ko_lines[i] for i, l in enumerate(ja_lines) if seed in l), "")),
        ])
    kanji_all = all_kanji + [r for r in seed_rows if r[2] >= 3]
    kanji_all.sort(key=lambda r: (-r[2], -r[3], r[0]))
    kanji_main = [r for r in kanji_all if r[2] >= 3]
    kanji_rare = [r for r in kanji_all if r[2] < 3]

    quoted_rows = build(quoted, quoted_indices)
    quoted_main = [r for r in quoted_rows if r[2] >= 3]
    quoted_rare = [r for r in quoted_rows if r[2] < 3]

    # 화자 이름 표(원문 이름은 영어, 번역 이름은 출력 name 필드에서 직접 집계)
    name_rows = []
    for name, st in name_stat.items():
        dist = name_ko.get(name, collections.Counter())
        total = sum(dist.values())
        variants = [(k, v, v / total if total else 0.0, 0.0) for k, v in dist.most_common(3)]
        empty_share = 1 - total / st["freq"] if st["freq"] else 0
        ex_i = name_indices[name][0]
        row = [
            name,
            st["freq"],
            len(st["files"]),
            fmt_variants(variants),
            split_flag(variants) if variants else 0,
            f"{empty_share*100:.0f}%",
            clip(records[ex_i][3]),
            clip(records[ex_i][4]),
        ]
        name_rows.append((st["freq"], len(st["files"]), name, row))
    name_rows.sort(key=lambda x: (-x[0], -x[1], x[2]))
    name_out = [r[3] for r in name_rows]

    # 빈도 3 미만 통합
    rare_rows = []
    for src, rows in (("katakana", kata_rare), ("kanji", kanji_rare), ("quoted", quoted_rare)):
        for r in rows:
            rare_rows.append([src] + r)
    rare_rows.sort(key=lambda r: (r[3], -r[4], r[1]))
    RARE_HEADER = ["source"] + KATA_HEADER

    KATA_OUT = KATA_HEADER
    n1 = write_tsv(os.path.join(out_dir, "ec_terms_katakana.tsv"), KATA_OUT, kata_main)
    n2 = write_tsv(
        os.path.join(out_dir, "ec_terms_names.tsv"),
        ["source_name", "freq", "files", "ko_variants", "split", "empty_ko_name_share",
         "example_ja", "example_ko"],
        name_out,
    )
    n3 = write_tsv(os.path.join(out_dir, "ec_terms_kanji.tsv"), KATA_OUT, kanji_main)
    n4 = write_tsv(os.path.join(out_dir, "ec_terms_quoted.tsv"), KATA_OUT, quoted_main)
    n5 = write_tsv(os.path.join(out_dir, "ec_terms_rare.tsv"), RARE_HEADER, rare_rows)

    # --- 기존 용어집 매칭 확인 ------------------------------------
    def count_ja(key: str) -> int:
        if not key:
            return 0
        if re.search(r"[぀-ヿ一-鿿]", key):
            return ja_text.count(key)
        # 영어 키는 단어 경계로 센다
        pat = r"(?<![A-Za-z0-9])" + re.escape(key) + r"(?![A-Za-z0-9])"
        return len(re.findall(pat, ja_text))

    dict_rows = []
    for key, ko, memo in dict_entries:
        jh = count_ja(key)
        kh = ko_text.count(ko) if ko else 0
        is_ja = 1 if re.search(r"[぀-ヿ一-鿿]", key) else 0
        if jh and kh:
            verdict = "ja+ko match"
        elif jh:
            verdict = "ja hit, ko value unused"
        elif kh:
            verdict = "ja 0 (key never appears), ko used"
        else:
            verdict = "no match at all"
        dict_rows.append((is_ja, jh, kh, key, [key, ko, memo, is_ja, jh, kh, verdict]))
    dict_rows.sort(key=lambda r: (-r[0], -r[1], -r[2], r[3]))
    n6 = write_tsv(
        os.path.join(out_dir, "old_dict_hits.tsv"),
        ["key", "ko", "memo", "key_is_japanese", "ja_hits", "ko_hits", "verdict"],
        [r[4] for r in dict_rows],
    )

    # --- 요약(보고용) ---------------------------------------------
    ja_keys_hit = sum(1 for r in dict_rows if r[0] == 1 and r[1] > 0)
    ja_keys_total = sum(1 for r in dict_rows if r[0] == 1)
    en_keys_hit = sum(1 for r in dict_rows if r[0] == 0 and r[1] > 0)
    en_keys_total = sum(1 for r in dict_rows if r[0] == 0)
    term_kata = [r for r in kata_main if r[1] == "term"]
    split_katakana = [r for r in term_kata if r[7] == 1]
    summary = {
        "files": file_count,
        "missing_output": len(missing_out),
        "entries": len(records),
        "rows": {
            "katakana": n1, "names": n2, "kanji": n3, "quoted": n4, "rare": n5,
            "old_dict_hits": n6,
        },
        "katakana_total_distinct": len(all_kata),
        "katakana_term_kind": len(term_kata),
        "kanji_distinct": len(all_kanji),
        "quoted_distinct": len(quoted_rows),
        "split_katakana_terms": len(split_katakana),
        "dict": {
            "total": len(dict_rows), "ja_keys": ja_keys_total, "ja_keys_with_hits": ja_keys_hit,
            "en_keys": en_keys_total, "en_keys_with_hits": en_keys_hit,
        },
        "top_katakana_term": [
            {"term": r[0], "freq": r[2], "files": r[3], "ko": r[6], "split": r[7]}
            for r in term_kata[:40]
        ],
        "split_examples": [
            {"term": r[0], "freq": r[2], "ko": r[6]} for r in split_katakana[:15]
        ],
        "top_names": [
            {"name": r[0], "freq": r[1], "ko": r[3], "split": r[4]} for r in name_out[:20]
        ],
        "dict_ja_keys_no_hit": [
            [r[2], r[1]] for r in dict_rows if r[0] == 1 and r[1] == 0
        ][:20],
        "dict_en_keys_with_ja_hits": [
            [r[2], r[1], r[4]] for r in dict_rows if r[0] == 0 and r[1] > 0
        ][:20],
    }
    with open(os.path.join(out_dir, "_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
