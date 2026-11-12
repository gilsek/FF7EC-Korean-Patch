#!/usr/bin/env python3
"""ui_ja_ko.tsv의 원문/번역 태그·자리표시자를 순서까지 비교한다. 복원은 하지 않는다.

usage: python ui_ja_tagcheck.py ui_ja_ko.tsv [--show 5]
"""

import csv
import re
import sys

csv.field_size_limit(10 ** 9)

TAG = re.compile(r'<[^<>\n]+>|\{[^{}\n]*\}')


def main(path, show=5):
    rows = list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))
    bad = []
    empty = 0
    for r in rows:
        ko = r['ko'] or ''
        if not ko.strip():
            empty += 1
            continue
        a = TAG.findall(r['ja'] or '')
        b = TAG.findall(ko)
        if a != b:
            bad.append(r)
    print('검사 행', len(rows) - empty)
    print('ko 빈 행', empty)
    print('태그/자리표시자 불일치', len(bad))
    for r in bad[:show]:
        a = TAG.findall(r['ja'] or '')
        b = TAG.findall(r['ko'] or '')
        print('---', r['file'], r['id'])
        print(' ja tags:', a)
        print(' ko tags:', b)
        print(' ja:', (r['ja'] or '').replace('\\n', '⏎')[:100])
        print(' ko:', (r['ko'] or '').replace('\\n', '⏎')[:100])


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        raise SystemExit('usage: python ui_ja_tagcheck.py ui_ja_ko.tsv [--show 5]')
    n = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 5
    main(sys.argv[1], n)
