#!/usr/bin/env python3
"""
GalTransl 출력 json -> 번역 표의 ko 열 가져오기.

사용법:
    python tools/gt_import.py OUT_DIR [--src-dir DIR] [--tl-dir DIR] [--overwrite]

    --src-dir    원본 story.tsv, ui.tsv 가 있는 폴더 (기본: work/tl). 읽기만 한다.
    --tl-dir     story_ko.tsv, ui_ko.tsv 를 쓸 폴더 (기본: work/tl).
    --overwrite  이미 ko가 있는 행도 덮어쓴다 (기본: 유지).

입력: OUT_DIR/gt_output/*.json (gt_input과 같은 구조, message가 번역문), OUT_DIR/gt_map.json
출력: TL_DIR/story_ko.tsv, TL_DIR/ui_ko.tsv  (원본 행과 열을 그대로 두고 ko 열만 채운다)
      OUT_DIR/_import_report.tsv  (열: json, index, source, ids, reason)

사유(reason):
    missing_output   매핑에 있는 json이 gt_output에 없음
    invalid_json     json을 읽을 수 없음
    count_mismatch   json 항목 수가 매핑과 다름 (해당 json 전체를 비워 둠)
    empty_message    message가 비었거나 공백만 있음
    orphan_output    gt_output에 있지만 매핑에 없는 json

번역문은 lua_escape(story) / ui_escape(ui)로 다시 이스케이프해서 쓴다.
사유가 있는 행은 ko를 비워 둔다 (원래 ko가 있었다면 그대로 둔다).
"""

import argparse
import csv
import json
import os
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_TL = os.path.join(ROOT, 'work', 'tl')

csv.field_size_limit(10 ** 9)


def lua_escape(s):
    """make_at_files.lua_unescape의 역변환. 백슬래시, 큰따옴표, LF, CR, 탭을 Lua 리터럴 형식으로 쓴다."""
    return (s.replace('\\', '\\\\').replace('"', '\\"')
             .replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'))


def ui_escape(s):
    """make_at_files.ui_unescape의 역변환. 백슬래시, 탭, CR, LF를 두 글자 이스케이프로 쓴다."""
    return (s.replace('\\', '\\\\').replace('\t', '\\t')
             .replace('\r', '\\r').replace('\n', '\\n'))


def read_raw(path):
    """헤더와 행 목록을 그대로 읽는다. 행 길이는 헤더에 맞춰 채우고, 빈 줄은 []로 둔다."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
        rows = []
        for row in reader:
            if not row:
                rows.append([])
                continue
            if len(row) < len(header):
                row = row + [''] * (len(header) - len(row))
            rows.append(row)
    return header, rows


def write_tsv(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(header)
        w.writerows(rows)


def row_id(kind, header, row):
    ci = {h: i for i, h in enumerate(header)}
    if kind == 'story':
        return row[ci['key']]
    return f"{row[ci['file']]}|{row[ci['id']]}"


def load_outputs(out_dir, gmap, report):
    """gt_output을 읽어 {kind: {행식별자: 이스케이프된 ko}} 를 만든다. 문제는 report에 쌓는다."""
    gt_out = os.path.join(out_dir, 'gt_output')
    fills = {'story': {}, 'ui': {}}

    def add(jname, i, ent, reason):
        report.append([jname, str(i), ent[0], ' ; '.join(ent[1:]), reason])

    for jname, entries in gmap.items():
        path = os.path.join(gt_out, jname)
        if not os.path.isfile(path):
            for i, ent in enumerate(entries):
                add(jname, i, ent, 'missing_output')
            continue
        try:
            with open(path, encoding='utf-8-sig') as f:
                data = json.load(f)
        except (OSError, ValueError):
            for i, ent in enumerate(entries):
                add(jname, i, ent, 'invalid_json')
            continue
        if not isinstance(data, list) or len(data) != len(entries):
            n = len(data) if isinstance(data, list) else 'not_list'
            for i, ent in enumerate(entries):
                add(jname, i, ent, f'count_mismatch(out={n},map={len(entries)})')
            continue
        for i, (ent, item) in enumerate(zip(entries, data)):
            msg = item.get('message') if isinstance(item, dict) else None
            if not isinstance(msg, str) or not msg.strip():
                add(jname, i, ent, 'empty_message')
                continue
            kind = ent[0]
            if kind == 'story':
                esc = lua_escape(msg)
            elif kind == 'ui':
                esc = ui_escape(msg)
            else:
                raise SystemExit(f'오류: 알 수 없는 source {kind!r} ({jname})')
            for rid in ent[1:]:
                fills[kind][rid] = esc

    if os.path.isdir(gt_out):
        for fn in sorted(os.listdir(gt_out)):
            if fn.endswith('.json') and fn not in gmap:
                report.append([fn, '', '', '', 'orphan_output'])
    return fills


def fill_rows(kind, header, rows, fills, overwrite, stats):
    ki = header.index('ko')
    for row in rows:
        if len(row) <= ki:
            continue
        val = fills.get(row_id(kind, header, row))
        if val is None:
            continue
        if row[ki].strip() and not overwrite:
            stats[kind]['kept'] += 1
            continue
        row[ki] = val
        stats[kind]['filled'] += 1


def import_all(src_dir, tl_dir, out_dir, overwrite=False):
    map_path = os.path.join(out_dir, 'gt_map.json')
    if not os.path.isfile(map_path):
        raise SystemExit(f'오류: 매핑 파일이 없음: {map_path} (먼저 gt_export.py를 실행)')
    with open(map_path, encoding='utf-8') as f:
        gmap = json.load(f, object_pairs_hook=OrderedDict)

    report = []
    fills = load_outputs(out_dir, gmap, report)

    os.makedirs(tl_dir, exist_ok=True)
    stats = {'story': {'filled': 0, 'kept': 0}, 'ui': {'filled': 0, 'kept': 0}}
    for kind, src_name, dst_name in (('story', 'story.tsv', 'story_ko.tsv'),
                                     ('ui', 'ui.tsv', 'ui_ko.tsv')):
        header, rows = read_raw(os.path.join(src_dir, src_name))
        if 'ko' not in header:
            raise SystemExit(f'오류: {src_name} 헤더에 ko 열이 없음')
        fill_rows(kind, header, rows, fills[kind], overwrite, stats)
        write_tsv(os.path.join(tl_dir, dst_name), header, rows)

    report_path = os.path.join(out_dir, '_import_report.tsv')
    write_tsv(report_path, ['json', 'index', 'source', 'ids', 'reason'], report)
    return {'stats': stats, 'problems': len(report), 'report': report_path, 'report_rows': report}


def main(argv=None):
    ap = argparse.ArgumentParser(description='GalTransl 출력 json -> TSV ko 열')
    ap.add_argument('out_dir')
    ap.add_argument('--src-dir', default=DEFAULT_TL)
    ap.add_argument('--tl-dir', default=DEFAULT_TL)
    ap.add_argument('--overwrite', action='store_true', help='이미 ko가 있는 행도 덮어쓴다')
    args = ap.parse_args(argv)
    res = import_all(os.path.abspath(args.src_dir), os.path.abspath(args.tl_dir),
                     os.path.abspath(args.out_dir), overwrite=args.overwrite)
    for kind, s in res['stats'].items():
        print(f'{kind}: 채움 {s["filled"]}, 기존 ko 유지 {s["kept"]}')
    print(f'문제 항목: {res["problems"]} -> {res["report"]}')
    print(f'출력: {os.path.abspath(args.tl_dir)}')
    return res


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
