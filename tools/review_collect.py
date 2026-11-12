#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Haiku 검수 결과(chunk_*.json)를 하나의 TSV로 모은다.

사용:
    python -I tools\\review_collect.py [--root <프로젝트루트>] [--review-dir <haiku폴더>] [--out <tsv경로>]

기본 경로는 이 스크립트 위치(tools/) 기준으로 프로젝트 루트를 찾는다.
기존 파일은 수정/삭제하지 않고, 출력 TSV만 새로 쓴다.
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

HEADER = [
    "chunk", "file", "idx", "type", "severity", "resolved",
    "name", "ja", "ko_now", "suggestion", "reason",
]

NL_MARK = "⏎"  # ⏎


def clean(value):
    """TSV 셀 값 정리: 줄바꿈 -> ⏎, 탭 -> 공백."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("\n", NL_MARK)
    value = value.replace("\t", " ")
    return value


def norm_ext(name):
    """file 이름에 .json 확장자가 없으면 붙인다."""
    name = (name or "").strip()
    if not name:
        return ""
    if not name.lower().endswith(".json"):
        name += ".json"
    return name


def to_int_idx(value):
    """idx를 정수로. 문자열/실수형 표기도 허용. 실패하면 None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value == int(value) else None
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"[+-]?\d+", s):
            return int(s)
        if re.fullmatch(r"[+-]?\d+\.0+", s):
            return int(float(s))
    return None


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def natural_key(text):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text)]


class GtCache:
    """gt_input / gt_output JSON을 한 번만 읽는다."""

    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self._cache = {}

    def get(self, filename):
        """(name, ja, ko_now) 또는 None(파일/행 없음)."""
        if filename not in self._cache:
            self._cache[filename] = self._load(filename)
        return self._cache[filename]

    def _load(self, filename):
        in_path = os.path.join(self.input_dir, filename)
        out_path = os.path.join(self.output_dir, filename)
        if not (os.path.isfile(in_path) and os.path.isfile(out_path)):
            return None
        try:
            src = load_json(in_path)
            dst = load_json(out_path)
        except (OSError, ValueError):
            return None
        if not isinstance(src, list) or not isinstance(dst, list):
            return None
        return (src, dst)

    @staticmethod
    def row(pair, idx):
        src, dst = pair
        if idx is None or idx < 0 or idx >= len(src) or idx >= len(dst):
            return None
        s = src[idx] if isinstance(src[idx], dict) else {}
        d = dst[idx] if isinstance(dst[idx], dict) else {}
        name = s.get("name", d.get("name", ""))
        ja = s.get("message", "")
        ko_now = d.get("message", "")
        if not isinstance(name, str):
            name = str(name)
        if not isinstance(ja, str):
            ja = str(ja)
        if not isinstance(ko_now, str):
            ko_now = str(ko_now)
        return (name, ja, ko_now)


def parse_args(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    default_root = os.path.dirname(here)
    ap = argparse.ArgumentParser(description="Haiku 검수 chunk JSON을 하나의 TSV로 모은다.")
    ap.add_argument("--root", default=default_root)
    ap.add_argument("--review-dir", default=None)
    ap.add_argument("--out", default=None)
    return ap.parse_args(argv)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args(argv)
    root = os.path.abspath(args.root)
    project = os.path.join(root, "gt_project_v2")
    review_dir = args.review_dir or os.path.join(project, "review", "haiku")
    input_dir = os.path.join(project, "gt_input")
    output_dir = os.path.join(project, "gt_output")
    out_path = args.out or os.path.join(project, "review", "haiku_all.tsv")

    chunk_paths = sorted(
        glob.glob(os.path.join(review_dir, "chunk_*.json")),
        key=lambda p: natural_key(os.path.basename(p)),
    )

    cache = GtCache(input_dir, output_dir)
    rows = []
    type_counts = Counter()
    sev_counts = Counter()
    unresolved = []
    skipped = []

    for path in chunk_paths:
        chunk = os.path.splitext(os.path.basename(path))[0]
        try:
            items = load_json(path)
        except (OSError, ValueError):
            skipped.append(chunk)
            continue
        if not isinstance(items, list):
            skipped.append(chunk)
            continue

        for item in items:
            if not isinstance(item, dict):
                skipped.append(chunk)
                continue
            filename = norm_ext(item.get("file", ""))
            idx = to_int_idx(item.get("idx"))
            itype = item.get("type", "")
            severity = item.get("severity", "")
            suggestion = item.get("suggestion", "")
            reason = item.get("reason", "")

            pair = cache.get(filename) if filename else None
            row_data = GtCache.row(pair, idx) if pair is not None else None
            resolved = "YES" if row_data is not None else "NO"
            if row_data is None:
                name, ja, ko_now = "", "", ""
                unresolved.append((chunk, filename, item.get("idx", "")))
            else:
                name, ja, ko_now = row_data

            rows.append([
                chunk, filename,
                "" if idx is None else idx,
                clean(itype), clean(severity), resolved,
                clean(name), clean(ja), clean(ko_now),
                clean(suggestion), clean(reason),
            ])
            type_counts[clean(itype) or "(없음)"] += 1
            sev_counts[clean(severity) or "(없음)"] += 1

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(HEADER) + "\n")
        for row in rows:
            fh.write("\t".join(str(c) for c in row) + "\n")

    # ---- 요약 (표준출력) ----
    print("chunk 파일: %d개 (읽음 %d, 건너뜀 %d)"
          % (len(chunk_paths), len(chunk_paths) - len(set(skipped)), len(set(skipped))))
    print("전체 건수: %d" % len(rows))
    print("type별:")
    for key, cnt in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-14s %d" % (key, cnt))
    print("severity별:")
    for key, cnt in sorted(sev_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-14s %d" % (key, cnt))
    print("resolved=NO: %d" % len(unresolved))
    if unresolved:
        for chunk, filename, raw_idx in unresolved[:20]:
            print("  %s | %s | idx=%s" % (chunk, filename or "(file없음)", raw_idx))
        if len(unresolved) > 20:
            print("  ... 외 %d건" % (len(unresolved) - 20))
    if skipped:
        print("건너뜀(파싱 불가/배열 아님): %s" % ", ".join(sorted(set(skipped))))
    print("출력: %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
