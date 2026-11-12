#!/usr/bin/env python3
"""
TSV 번역 표 -> GalTransl 입력 json 내보내기.

사용법:
    python tools/gt_export.py OUT_DIR [--src-lang {ja,en}] [--speakers PATH] [--src-dir DIR]

    --src-lang  message로 내보낼 원문 언어 (기본: ja). ja이면 ja 열, 비었거나 자리표시자/태그가
                en과 맞지 않으면 en으로 대체한다. en이면 en 열만 쓴다.
    --speakers  열 key, speaker 인 TSV. story 항목의 name에 넣는다. 없으면 name은 빈 문자열.
    --src-dir   story.tsv, ui.tsv 가 있는 폴더 (기본: work/tl). 읽기만 한다.

출력 (OUT_DIR 아래):
    gt_input/story__<file>.json        장면(file 값) 하나당 json, 표 순서 유지
    gt_input/ui__<file>.json           ui 파일 하나당 json (500개 초과 시 ui__<file>__001.json ...)
    gt_map.json                        {json파일명: [[source, 행식별자...], ...]}
    gt_srclang.json                    {json파일명: ["ja"|"en", ...]} 항목별 실제 원문 언어
    _src_fallback.tsv                  en으로 대체한 항목 (source, id, reason, en, ja)

json 형식: [{"name": "...", "message": "..."}], UTF-8, ensure_ascii=False, indent=2.
message는 이스케이프를 해제한 실제 텍스트다.

건너뛰는 행: en 기준으로 이스케이프 해제 후 알파벳이 하나도 없는 행 (빈 값, 공백, 숫자, 기호만 있는 행).
ui는 표 전체에서 en이 같은 행을 하나로 합친다. 메시지는 처음 나온 행의 파일에 넣고,
gt_map에는 같은 en의 모든 행 식별자("file|id")를 연결한다. 같은 en에 ja가 여러 개면
처음 나온 비어 있지 않은 ja를 쓰고, 다른 ja 값의 개수만 집계한다.
story는 행마다 하나씩 내보낸다 (같은 en이어도 합치지 않는다).

대체 사유(reason): ja_empty, placeholder_mismatch, tag_mismatch
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from make_at_files import lua_unescape, ui_unescape  # noqa: E402

ROOT = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(ROOT, 'work', 'tl')
DEFAULT_SPEAKERS = os.path.join(DEFAULT_SRC, 'speakers.tsv')
CHUNK = 500

PH_RE = re.compile(r'\{[^{}\n]*\}')
TAG_RE = re.compile(r'<[^<>\n]+>')
BRK_RE = re.compile(r'\[[υμ]\]')

csv.field_size_limit(10 ** 9)


def has_alpha(text):
    return any(ch.isalpha() for ch in text)


def placeholders(text):
    return Counter(PH_RE.findall(text))


def tag_names(text):
    """태그 이름 목록. <i> -> i, </i> -> /i, <c_color=#f00> -> c_color, [υ] 와 [μ] 는 그대로."""
    names = []
    for t in TAG_RE.findall(text):
        body = t[1:-1].strip()
        names.append(re.split(r'[=\s]', body, maxsplit=1)[0])
    names.extend(BRK_RE.findall(text))
    return sorted(names)


def pick_ja(en_text, ja_raw, unescape):
    """ja를 쓸 수 있으면 (ja 텍스트, None), 아니면 (en 텍스트, 사유)를 돌려준다."""
    if not ja_raw.strip():
        return en_text, 'ja_empty'
    ja_text = unescape(ja_raw)
    if not ja_text.strip():
        return en_text, 'ja_empty'
    if placeholders(en_text) != placeholders(ja_text):
        return en_text, 'placeholder_mismatch'
    # 영어판이 강조용으로만 붙인 <i>/<b>는 일본어에 없어도 된다
    style = {'i', '/i', 'b', '/b'}
    if [t for t in tag_names(en_text) if t not in style] != [t for t in tag_names(ja_text) if t not in style]:
        return en_text, 'tag_mismatch'
    return ja_text, None


def read_table(path, cols):
    """표를 읽어 cols 열만 담은 dict 리스트로 돌려준다. 완전히 빈 행은 버린다."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        try:
            header = next(reader)
        except StopIteration:
            return []
        idx = {h.strip(): i for i, h in enumerate(header)}
        missing = [c for c in cols if c not in idx]
        if missing:
            raise SystemExit(f'오류: {path} 헤더에 열 {missing} 이 없음 (헤더: {header})')
        rows = []
        for row in reader:
            if not any(x.strip() for x in row):
                continue
            rows.append({c: (row[idx[c]] if idx[c] < len(row) else '') for c in cols})
        return rows


def read_speakers(path):
    if not os.path.isfile(path):
        print(f'경고: speakers 파일이 없어 story name을 모두 빈 문자열로 둡니다: {path}')
        return {}
    speakers = {}
    for r in read_table(path, ['key', 'speaker']):
        name = r['speaker'].strip()
        if name.startswith('('):  # 예: (UNUSED) 같은 자리표시 값은 화자가 아님
            name = ''
        speakers[r['key']] = name
    return speakers


def safe(name):
    return name.replace('/', '__').replace('\\', '__')


def write_json(path, data):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def write_tsv(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(header)
        w.writerows(rows)


def export(src_dir, speakers_path, out_dir, src_lang='ja'):
    if src_lang not in ('ja', 'en'):
        raise SystemExit(f'오류: --src-lang 은 ja 또는 en 이어야 함: {src_lang}')
    use_ja = src_lang == 'ja'
    gt_in = os.path.join(out_dir, 'gt_input')
    os.makedirs(gt_in, exist_ok=True)
    for fn in os.listdir(gt_in):  # 이전 실행의 json만 지운다 (gt_input 안에서만)
        if fn.endswith('.json'):
            os.remove(os.path.join(gt_in, fn))

    speakers = read_speakers(speakers_path)
    gmap = OrderedDict()
    srclang = OrderedDict()
    fallback = []  # [source, id, reason, en, ja]
    stats = OrderedDict([
        ('story_json', 0), ('story_msgs', 0), ('story_skipped', 0), ('story_named', 0),
        ('story_src_ja', 0), ('story_src_en', 0),
        ('story_fb_ja_empty', 0), ('story_fb_placeholder_mismatch', 0), ('story_fb_tag_mismatch', 0),
        ('ui_json', 0), ('ui_msgs', 0), ('ui_skipped', 0), ('ui_rows_mapped', 0), ('ui_merged', 0),
        ('ui_src_ja', 0), ('ui_src_en', 0),
        ('ui_fb_ja_empty', 0), ('ui_fb_placeholder_mismatch', 0), ('ui_fb_tag_mismatch', 0),
        ('ui_ja_variant_groups', 0), ('ui_ja_extra_values', 0),
    ])

    def emit(name, items, entries, langs):
        if name in gmap:
            raise SystemExit(f'오류: json 파일명 충돌: {name}')
        write_json(os.path.join(gt_in, name), items)
        gmap[name] = entries
        srclang[name] = langs

    # story: 파일(장면)별, 표 순서 유지
    story_cols = ['key', 'file', 'en'] + (['ja'] if use_ja else [])
    story_rows = read_table(os.path.join(src_dir, 'story.tsv'), story_cols)
    story_groups = OrderedDict()
    for r in story_rows:
        en_text = lua_unescape(r['en'])
        if not has_alpha(en_text):
            stats['story_skipped'] += 1
            continue
        if use_ja:
            text, reason = pick_ja(en_text, r['ja'], lua_unescape)
            if reason:
                stats['story_fb_' + reason] += 1
                fallback.append(['story', r['key'], reason, r['en'], r['ja']])
                stats['story_src_en'] += 1
                lang = 'en'
            else:
                stats['story_src_ja'] += 1
                lang = 'ja'
        else:
            text, lang = en_text, 'en'
            stats['story_src_en'] += 1
        story_groups.setdefault(r['file'], []).append((r['key'], text, lang))
    for file, lst in story_groups.items():
        items, entries, langs = [], [], []
        for key, text, lang in lst:
            name = speakers.get(key, '')
            if name:
                stats['story_named'] += 1
            items.append({'name': name, 'message': text})
            entries.append(['story', key])
            langs.append(lang)
        emit('story__' + safe(file) + '.json', items, entries, langs)
        stats['story_json'] += 1
        stats['story_msgs'] += len(items)

    # ui: en 기준으로 전체 표에서 합친다
    ui_cols = ['file', 'id', 'en'] + (['ja'] if use_ja else [])
    ui_rows = read_table(os.path.join(src_dir, 'ui.tsv'), ui_cols)
    uniq = OrderedDict()  # 원문 en 셀 -> {text_en, file, ids, ja_first, ja_vals}
    for r in ui_rows:
        text_en = ui_unescape(r['en'])
        if not has_alpha(text_en):
            stats['ui_skipped'] += 1
            continue
        e = uniq.get(r['en'])
        if e is None:
            e = uniq[r['en']] = {'text_en': text_en, 'file': r['file'], 'ids': [],
                                 'ja_first': None, 'ja_vals': []}
        e['ids'].append(f"{r['file']}|{r['id']}")
        if use_ja and r['ja'].strip():
            if e['ja_first'] is None:
                e['ja_first'] = r['ja']
            if r['ja'] not in e['ja_vals']:
                e['ja_vals'].append(r['ja'])
        stats['ui_rows_mapped'] += 1
    stats['ui_merged'] = stats['ui_rows_mapped'] - len(uniq)

    ui_groups = OrderedDict()
    for key_en, e in uniq.items():
        if use_ja:
            ja_raw = e['ja_first'] or ''
            text, reason = pick_ja(e['text_en'], ja_raw, ui_unescape)
            if reason:
                stats['ui_fb_' + reason] += 1
                fallback.append(['ui', ' ; '.join(e['ids']), reason, key_en, ja_raw])
                stats['ui_src_en'] += 1
                lang = 'en'
            else:
                stats['ui_src_ja'] += 1
                lang = 'ja'
            if len(e['ja_vals']) > 1:
                stats['ui_ja_variant_groups'] += 1
                stats['ui_ja_extra_values'] += len(e['ja_vals']) - 1
        else:
            text, lang = e['text_en'], 'en'
            stats['ui_src_en'] += 1
        e['text'], e['lang'] = text, lang
        ui_groups.setdefault(e['file'], []).append(e)

    for file, lst in ui_groups.items():
        base = 'ui__' + safe(file)
        nchunks = max(1, math.ceil(len(lst) / CHUNK))
        for ci in range(nchunks):
            part = lst[ci * CHUNK:(ci + 1) * CHUNK]
            name = base + '.json' if nchunks == 1 else f'{base}__{ci + 1:03d}.json'
            items = [{'name': '', 'message': e['text']} for e in part]
            entries = [['ui', *e['ids']] for e in part]
            langs = [e['lang'] for e in part]
            emit(name, items, entries, langs)
            stats['ui_json'] += 1
            stats['ui_msgs'] += len(items)

    write_json(os.path.join(out_dir, 'gt_map.json'), gmap)
    write_json(os.path.join(out_dir, 'gt_srclang.json'), srclang)
    write_tsv(os.path.join(out_dir, '_src_fallback.tsv'),
              ['source', 'id', 'reason', 'en', 'ja'], fallback)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description='TSV -> GalTransl 입력 json')
    ap.add_argument('out_dir')
    ap.add_argument('--src-lang', choices=['ja', 'en'], default='ja')
    ap.add_argument('--speakers', default=DEFAULT_SPEAKERS)
    ap.add_argument('--src-dir', default=DEFAULT_SRC)
    args = ap.parse_args(argv)
    out_dir = os.path.abspath(args.out_dir)
    stats = export(os.path.abspath(args.src_dir), os.path.abspath(args.speakers), out_dir,
                   src_lang=args.src_lang)
    for k, v in stats.items():
        print(f'{k}: {v}')
    print(f'json 파일 수: {stats["story_json"] + stats["ui_json"]} -> {os.path.join(out_dir, "gt_input")}')
    print(f'매핑: {os.path.join(out_dir, "gt_map.json")}')
    return stats


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
