#!/usr/bin/env python3
"""ja_map.tsv의 일본어 UI 행을 일본어 원문 기준으로 GalTransl 입력으로 내보낸다.

usage: python ui_ja_export.py JA_MAP.tsv PROJECT_DIR

- ja_map.tsv: 열 file,id,ja,en_file,en (탭 구분, csv.DictReader로 읽는다)
- ja에 가나/한자가 있는 행만 쓴다.
- 리터럴 두 글자 `\\n`은 실제 개행으로 바꾼 뒤, 같은 텍스트를 하나로 합친다 (처음 나온 순서 유지).
- PROJECT_DIR/gt_input/ui_ja__NNN.json 에 500개씩 [{"name":"","message":...}] 형식으로 쓴다.
- PROJECT_DIR/ja_map_index.json: {json파일명: [원본 ja 문자열, ...]} (리터럴 `\\n` 표기 그대로)
"""

import csv
import json
import os
import re
import sys
from collections import OrderedDict

csv.field_size_limit(10 ** 9)

JP = re.compile(r'[぀-ヿ一-鿿]')
CHUNK = 500


def to_text(raw):
    """리터럴 두 글자 \\n 을 실제 개행으로 바꾼다."""
    return raw.replace('\\n', '\n')


def main(ja_map, project):
    rows = list(csv.DictReader(open(ja_map, encoding='utf-8'), delimiter='\t'))
    missing = [c for c in ('file', 'id', 'ja', 'en_file', 'en') if c not in (rows[0] if rows else {})]
    if missing:
        raise SystemExit(f'오류: {ja_map} 헤더에 열이 없음: {missing}')

    uniq = OrderedDict()  # 실제 텍스트 -> 원본 ja 문자열
    jp_rows = 0
    for r in rows:
        raw = r['ja'] or ''
        if not JP.search(raw):
            continue
        jp_rows += 1
        text = to_text(raw)
        if text not in uniq:
            uniq[text] = raw

    gt_in = os.path.join(project, 'gt_input')
    os.makedirs(gt_in, exist_ok=True)
    for fn in os.listdir(gt_in):  # 이전 실행의 ui_ja 입력만 지운다
        if fn.startswith('ui_ja__') and fn.endswith('.json'):
            os.remove(os.path.join(gt_in, fn))

    texts = list(uniq)
    index = OrderedDict()
    nfiles = max(1, -(-len(texts) // CHUNK))
    for ci in range(nfiles):
        part = texts[ci * CHUNK:(ci + 1) * CHUNK]
        name = f'ui_ja__{ci + 1:03d}.json'
        items = [{'name': '', 'message': t} for t in part]
        with open(os.path.join(gt_in, name), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.write('\n')
        index[name] = [uniq[t] for t in part]

    with open(os.path.join(project, 'ja_map_index.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print('일본어 행', jp_rows)
    print('고유 메시지', len(texts))
    print('중복으로 합쳐진 행', jp_rows - len(texts))
    print('json 파일', nfiles, '->', gt_in)
    print('매핑', os.path.join(project, 'ja_map_index.json'))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) != 3:
        raise SystemExit('usage: python ui_ja_export.py JA_MAP.tsv PROJECT_DIR')
    main(sys.argv[1], sys.argv[2])
