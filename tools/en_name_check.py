#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""영어 원문 UI 번역에서 고유명사 표기가 용어집과 어긋난 곳을 찾는다.

읽기 전용 입력:
  - gt_project_ui_v2/Dict/gpt_dict.txt      (일본어<TAB>한국어<TAB>설명)
  - work/ja_ui_research/ja_map.tsv          (시트<TAB>id<TAB>일본어<TAB>영어시트<TAB>영어)
  - gt_project_ui_v2/gt_input/*.json, gt_output/*.json

출력:
  - work/en_name_map.tsv        (영어<TAB>한국어<TAB>일본어<TAB>근거 행 수)
  - work/en_name_mismatch.tsv   (파일<TAB>idx<TAB>영어이름<TAB>기대한국어<TAB>원문80<TAB>번역80)
  - work/en_name_summary.txt    (상위 60개 불일치 이름 + 실제 표기 후보)
"""

import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_PATH = os.path.join(BASE, "gt_project_ui_v2", "Dict", "gpt_dict.txt")
JA_MAP_PATH = os.path.join(BASE, "work", "ja_ui_research", "ja_map.tsv")
IN_DIR = os.path.join(BASE, "gt_project_ui_v2", "gt_input")
OUT_DIR = os.path.join(BASE, "gt_project_ui_v2", "gt_output")
WORK_DIR = os.path.join(BASE, "work")
MAP_OUT = os.path.join(WORK_DIR, "en_name_map.tsv")
MISMATCH_OUT = os.path.join(WORK_DIR, "en_name_mismatch.tsv")
SUMMARY_OUT = os.path.join(WORK_DIR, "en_name_summary.txt")

MAX_EN_LEN = 40


def load_glossary(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            ja, ko = parts[0].strip(), parts[1].strip()
            if ja and ko:
                entries.append((ja, ko))
    return entries


def load_ja_map(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)
        for r in reader:
            if len(r) < 5:
                continue
            rows.append(r)
    return rows


def is_generic_word(en):
    """일반 단어처럼 보이는 것: 전부 소문자이거나 숫자/기호뿐."""
    if en.islower():
        return True
    if not any(c.isalpha() for c in en):
        return True
    return False


def build_name_map(glossary, ja_rows):
    # 용어집 일본어 -> 한국어
    ko_of_ja = {}
    for ja, ko in glossary:
        ko_of_ja.setdefault(ja, set()).add(ko)

    evidence = Counter()          # (en, ko) -> 행 수
    ja_of = defaultdict(Counter)  # en -> Counter(ja)
    for r in ja_rows:
        ja = r[2].strip()
        if ja not in ko_of_ja:
            continue
        en = r[4].strip()
        if not en or len(en) < 3 or len(en) > MAX_EN_LEN:
            continue
        if is_generic_word(en):
            continue
        for ko in ko_of_ja[ja]:
            evidence[(en, ko)] += 1
            ja_of[en][ja] += 1

    name_map = {}
    conflicts = {}
    by_en = defaultdict(Counter)
    for (en, ko), n in evidence.items():
        by_en[en][ko] = n
    for en, koc in by_en.items():
        ranked = koc.most_common()
        best_ko, best_n = ranked[0]
        # 동률이면 사전순으로 안정 정렬
        ties = [ko for ko, n in ranked if n == best_n]
        best_ko = sorted(ties)[0]
        name_map[en] = best_ko
        if len(ranked) > 1:
            conflicts[en] = sorted(ranked, key=lambda x: (-x[1], x[0]))
    return name_map, evidence, ja_of, conflicts


HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
HANGUL_RE = re.compile(r"[가-힣]+")


def decompose(ch):
    code = ord(ch) - HANGUL_START
    if code < 0 or code > HANGUL_END - HANGUL_START:
        return None
    cho = code // 588
    jung = (code % 588) // 28
    return cho, jung


def similarity(expected, token):
    """기대 표기와 후보 한글 단어의 대략적 유사도 (0=무관)."""
    if not expected or not token:
        return 0
    score = 0
    if token[0] == expected[0]:
        score += 3
    else:
        d1 = decompose(token[0])
        d2 = decompose(expected[0])
        if d1 and d2:
            if d1[0] == d2[0]:
                score += 2 if d1[1] == d2[1] else 1
    if len(token) == len(expected):
        score += 1
    elif abs(len(token) - len(expected)) <= 1:
        score += 0
    else:
        score -= 1
    return max(score, 0)


def check_names(name_map, in_dir, out_dir):
    # 긴 이름 우선 매칭
    names_sorted = sorted(name_map, key=len, reverse=True)
    patterns = [(n, re.compile(r"\b" + re.escape(n) + r"\b")) for n in names_sorted]

    files = sorted(f for f in os.listdir(in_dir) if f.endswith(".json"))
    mismatches = []  # (file, idx, en_name, expected_ko, en_text, ko_text)
    for fname in files:
        out_path = os.path.join(out_dir, fname)
        if not os.path.exists(out_path):
            continue
        with open(os.path.join(in_dir, fname), encoding="utf-8") as f:
            src = json.load(f)
        with open(out_path, encoding="utf-8") as f:
            dst = json.load(f)
        n = min(len(src), len(dst))
        for i in range(n):
            en_text = src[i].get("message") or ""
            ko_text = dst[i].get("message") or ""
            if not en_text:
                continue
            occupied = []
            seen_here = set()
            for name, pat in patterns:
                if name not in en_text:
                    continue
                expected = name_map[name]
                for m in pat.finditer(en_text):
                    s, e = m.span()
                    if any(not (e <= os_ or s >= oe) for os_, oe in occupied):
                        continue
                    occupied.append((s, e))
                    if expected in ko_text:
                        continue
                    if name in seen_here:
                        continue
                    seen_here.add(name)
                    mismatches.append((fname, i, name, expected, en_text, ko_text))
    return mismatches, len(files)


def global_token_counts(out_dir):
    """번역문 전체에서 한글 토큰 빈도. 흔한 단어를 후보에서 걸러내는 용도."""
    counts = Counter()
    for fname in os.listdir(out_dir):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(out_dir, fname), encoding="utf-8") as f:
            data = json.load(f)
        for row in data:
            counts.update(HANGUL_RE.findall(row.get("message") or ""))
    return counts


def pick_candidates(name, expected, texts, glob):
    """불일치 행들의 번역문에서 실제 표기 후보를 뽑는다 (근사)."""
    local = Counter()
    verbatim = 0
    for text in texts:
        if name in text:
            verbatim += 1
        for tok in set(HANGUL_RE.findall(text)):
            if len(tok) >= 2:
                local[tok] += 1
    scored = {}
    for tok, hits in local.items():
        sim = similarity(expected, tok)
        rarity = 1.0 + math.log10(glob.get(tok, 0) + 1)
        scored[tok] = hits * (1 + sim) / rarity
    ranked = sorted(scored.items(), key=lambda x: (-x[1], x[0]))
    out = []
    if texts and verbatim / float(len(texts)) >= 0.25:
        out.append("영문 유지(%d/%d)" % (verbatim, len(texts)))
    for tok, _score in ranked[: 3 - len(out)]:
        out.append("%s(%d)" % (tok, local[tok]))
    return ", ".join(out) if out else "-"


def build_summary(name_map, mismatches, conflicts, glob, out_path):
    counts = Counter(m[2] for m in mismatches)
    per_name_texts = defaultdict(list)
    for fname, idx, name, expected, en_text, ko_text in mismatches:
        per_name_texts[name].append(ko_text)

    lines = []
    lines.append("영어 고유명사 표기 점검 요약")
    lines.append("")
    lines.append("대응표 이름 수: %d" % len(name_map))
    lines.append("충돌 이름 수: %d" % len(conflicts))
    lines.append("불일치 총 건수: %d" % len(mismatches))
    lines.append("불일치 이름 종류: %d" % len(counts))
    lines.append("")
    lines.append("== 상위 60개 불일치 이름 ==")
    lines.append("후보는 번역문 한글 단어 빈도 + 기대 표기 유사도 근사치이며 정확한 대응이 아님.")
    lines.append("건수\t영어\t기대한국어\t실제 표기 후보(근사)\t예시 번역")
    for name, cnt in counts.most_common(60):
        expected = name_map[name]
        cands = pick_candidates(name, expected, per_name_texts[name], glob)
        sample = per_name_texts[name][0].replace("\t", " ").replace("\n", " ")[:70]
        lines.append("%d\t%s\t%s\t%s\t%s" % (cnt, name, expected, cands, sample))
    lines.append("")
    lines.append("== 충돌 (같은 영어에 한국어 후보 여러 개, 빈도순) ==")
    for en in sorted(conflicts):
        items = conflicts[en]
        lines.append("%s -> %s" % (en, ", ".join("%s(%d)" % (ko, n) for ko, n in items)))
    if not conflicts:
        lines.append("(없음)")
    lines.append("")

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main():
    glossary = load_glossary(DICT_PATH)
    ja_rows = load_ja_map(JA_MAP_PATH)
    name_map, evidence, ja_of, conflicts = build_name_map(glossary, ja_rows)

    with open(MAP_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("english\tkorean\tjapanese\tcount\n")
        for en in sorted(name_map, key=lambda x: (-evidence[(x, name_map[x])], x)):
            ja = ja_of[en].most_common(1)[0][0]
            f.write("%s\t%s\t%s\t%d\n" % (en, name_map[en], ja, evidence[(en, name_map[en])]))

    mismatches, n_files = check_names(name_map, IN_DIR, OUT_DIR)

    with open(MISMATCH_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("file\tidx\tenglish\texpected_korean\tsource80\ttranslation80\n")
        for fname, idx, name, expected, en_text, ko_text in mismatches:
            en80 = en_text.replace("\t", " ").replace("\n", " ")[:80]
            ko80 = ko_text.replace("\t", " ").replace("\n", " ")[:80]
            f.write("%s\t%d\t%s\t%s\t%s\t%s\n" % (fname, idx, name, expected, en80, ko80))

    build_summary(name_map, mismatches, conflicts, global_token_counts(OUT_DIR), SUMMARY_OUT)

    counts = Counter(m[2] for m in mismatches)
    print("files scanned: %d" % n_files)
    print("name map: %d" % len(name_map))
    print("conflicts: %d" % len(conflicts))
    print("mismatch rows: %d" % len(mismatches))
    print("mismatch name kinds: %d" % len(counts))
    for name, cnt in counts.most_common(15):
        print("  %-22s -> %-10s %4d" % (name, name_map[name], cnt))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
