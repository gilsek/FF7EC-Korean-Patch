#!/usr/bin/env python3
"""GalTransl 출력(일본어 원문 기준)을 ja_map.tsv의 모든 일본어 행 ko 열로 붙인다.

usage: python ui_ja_import.py JA_MAP.tsv PROJECT_DIR OUT_TSV

- PROJECT_DIR/ja_map_index.json 으로 json 항목 ↔ 원본 ja 문자열을 맞춘다.
- 원본 ja의 리터럴 `\\n`을 실제 개행으로 바꾼 텍스트를 키로 번역을 찾는다.
- 번역의 실제 개행은 다시 리터럴 `\\n` 두 글자로 되돌려 표에 쓴다.
- OUT_TSV 열: file, id, ja, en, ko (일본어 행 전체, 중복 포함)
"""

import csv
import json
import os
import re
import sys
from collections import OrderedDict

csv.field_size_limit(10 ** 9)

JP = re.compile(r'[぀-ヿ一-鿿]')


def to_text(raw):
    return raw.replace('\\n', '\n')


def to_esc(text):
    """실제 개행을 리터럴 두 글자 \\n 으로 되돌린다."""
    return text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')


def load_index(project):
    path = os.path.join(project, 'ja_map_index.json')
    if not os.path.isfile(path):
        raise SystemExit(f'오류: 매핑 파일이 없음: {path} (먼저 ui_ja_export.py 실행)')
    with open(path, encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def build_ko(project, index):
    ko = {}
    report = []
    for name, raws in index.items():
        path = os.path.join(project, 'gt_output', name)
        if not os.path.isfile(path):
            report.append([name, '', 'missing_output'])
            continue
        try:
            with open(path, encoding='utf-8-sig') as f:
                data = json.load(f)
        except (OSError, ValueError):
            report.append([name, '', 'invalid_json'])
            continue
        if not isinstance(data, list) or len(data) != len(raws):
            n = len(data) if isinstance(data, list) else 'not_list'
            report.append([name, '', f'count_mismatch(out={n},map={len(raws)})'])
            continue
        for i, (raw, item) in enumerate(zip(raws, data)):
            msg = item.get('message') if isinstance(item, dict) else None
            if not isinstance(msg, str) or not msg.strip():
                report.append([name, str(i), 'empty_message'])
                continue
            key = to_text(raw)
            if key in ko and ko[key] != msg:
                report.append([name, str(i), 'duplicate_key_diff'])
            ko[key] = msg
    return ko, report


def main(ja_map, project, out_tsv):
    index = load_index(project)
    ko, report = build_ko(project, index)

    rows = list(csv.DictReader(open(ja_map, encoding='utf-8'), delimiter='\t'))
    out = []
    filled = 0
    for r in rows:
        raw = r['ja'] or ''
        if not JP.search(raw):
            continue
        val = ko.get(to_text(raw))
        if val is not None:
            filled += 1
            val = to_esc(val)
        else:
            val = ''
            report.append([r['file'], r['id'], 'no_translation'])
        out.append([r['file'], r['id'], raw, r['en'], val])

    os.makedirs(os.path.dirname(os.path.abspath(out_tsv)) or '.', exist_ok=True)
    with open(out_tsv, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(['file', 'id', 'ja', 'en', 'ko'])
        w.writerows(out)

    print('출력 행', len(out))
    print('ko 채움', filled)
    print('ko 빈 행', len(out) - filled)
    print('번역 키', len(ko))
    print('문제', len(report))
    for r in report[:20]:
        print('problem', r)
    print('출력', os.path.abspath(out_tsv))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) != 4:
        raise SystemExit('usage: python ui_ja_import.py JA_MAP.tsv PROJECT_DIR OUT_TSV')
    main(*sys.argv[1:4])
