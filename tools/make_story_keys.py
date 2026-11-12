#!/usr/bin/env python3
"""work/tl/story_ko.tsv -> StoryKo plugin data file (KEY<TAB>KO, no header, UTF-8 no BOM, LF).

입력 열: key, file, en, ja, ko (탭 구분). ko는 이미 Lua 리터럴 이스케이프 상태이므로 그대로 쓴다.
규칙:
  - ko가 빈 행은 제외
  - 키 중복은 첫 번째 (ko가 비어 있지 않은) 값만 사용
  - ko에 실제 탭/CR/LF가 있으면 해당 행을 제외하고 보고
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_PATH = os.path.join(ROOT, "work", "tl", "story_ko.tsv")
OUT_PATH = os.path.join(ROOT, "work", "storyko", "story_ko.tsv")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(IN_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        rows = list(reader)

    if not rows:
        print("입력이 비어 있다", file=sys.stderr)
        return 1

    header = [h.strip() for h in rows[0]]
    if header[:5] != ["key", "file", "en", "ja", "ko"]:
        print("예상 헤더와 다르다: %r" % header, file=sys.stderr)
        return 1

    data = rows[1:]
    seen_keys = set()
    empty_ko = 0
    bad_rows = []          # 열 개수 이상 또는 ko에 제어 문자
    dup_rows = 0
    out = {}               # key -> ko (순서 유지)

    for lineno, r in enumerate(data, start=2):
        if not r or not r[0].strip():
            continue
        if r[0] in seen_keys:
            dup_rows += 1
        seen_keys.add(r[0])

        if len(r) != 5:
            bad_rows.append((lineno, r[0], "열 개수 %d" % len(r)))
            continue

        key, ko = r[0], r[4]
        if ko == "":
            empty_ko += 1
            continue
        if "\t" in ko or "\r" in ko or "\n" in ko:
            bad_rows.append((lineno, key, "ko에 제어 문자"))
            continue
        if key in out:
            continue  # 첫 번째 값만
        out[key] = ko

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        for key, ko in out.items():
            f.write(key + "\t" + ko + "\n")

    print("출력: %s" % OUT_PATH)
    print("전체 키(고유): %d" % len(seen_keys))
    print("ko 있는 키(출력): %d" % len(out))
    print("제외 - ko 빈 값: %d" % empty_ko)
    print("제외 - 기타(열 오류/제어 문자): %d" % len(bad_rows))
    print("키 중복 행(무시됨): %d" % dup_rows)
    for lineno, key, why in bad_rows[:20]:
        print("  경고 줄 %d %s: %s" % (lineno, key, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
