#!/usr/bin/env python3
"""
TSV 번역 표 -> XUnity.AutoTranslator(AT) 텍스트 번역 파일 변환기.

사용법:
    python tools/make_at_files.py OUT_DIR [--story PATH] [--ui PATH]

출력 (OUT_DIR 아래):
    story.txt, ui.txt         원문=번역, 한 줄에 하나. UTF-8(BOM 없음), 줄 끝 LF
    _conflicts.tsv            같은 원문에 서로 다른 번역이 온 행 (첫 번째 번역을 유지)
    _pending_tags.tsv         story 원문에 <c_color= / <c_size= 가 있어 보류한 행
    _warnings.tsv             자리표시자/태그/줄바꿈/깨짐/백슬래시/특수 접두사 검사 결과

입력 TSV: UTF-8, 첫 줄 헤더, 탭 구분.
    story.tsv: key, file, en, ja, ko   (en/ko는 Lua 문자열 리터럴 내용)
    ui.tsv:    file, id, en, ja, ko    (en/ko는 \\ \\t \\r \\n 으로 이스케이프된 값)
    csv 모듈은 QUOTE_NONE으로 읽는다. 원문에 큰따옴표가 많아서 기본 quoting이면
    "로 시작하는 셀이 잘못 파싱되기 때문이다.

이스케이프 규칙 (README "(AutoTranslator).md" 및 게임 폴더 기존 파일로 확인)
  [확인됨]
    - 한 줄에 `원문=번역`. 줄바꿈은 파일 안에서 두 글자 `\\n`으로 쓴다.
      근거: README 텍스트 조회 예시(`\\n` 표기), 게임 폴더의
      BepInEx/Translation/ko/Text/_test.txt 의 `This way,\\nmerc!=이쪽이야,\\n용병!` 줄.
    - `r:` 로 시작하는 원문은 정규식 항목, `sr:` 는 분할 정규식 항목이다 (README 정규식 절).
    - `#` 로 시작하는 줄은 디렉티브(#set, #unset, #enable fallback)다 (README 범위 지정 절).
  [추정 - README에 명시 없음, 보수적으로 처리]
    - CR(\\r)은 \\r 로 쓴다 (LF와 같은 방식이라 가정).
    - 탭, 백슬래시, '=' 는 이스케이프하지 않고 그대로 쓴다.
      대신 원문/번역에 백슬래시가 있거나 원문에 '='가 있으면 _warnings.tsv에 남긴다.
    - '//' 로 시작하는 원문은 주석으로 오인될 수 있어 건너뛰고 경고한다.
    - 원문과 번역에서 줄 수, 자리표시자, 태그가 맞지 않아도 출력은 하고 경고만 남긴다.

입력 언이스케이프
    story: Lua 규칙. \\n \\t \\r \\a \\b \\f \\v \\\\ \\" \\' \\ddd \\xXX \\z \\u{XXX}, 백슬래시+실제 줄바꿈.
    ui:    \\\\ \\t \\r \\n 만 복원. 그 외 \\X 는 그대로 둔다.
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STORY = os.path.join(ROOT, 'work', 'tl', 'story.tsv')
DEFAULT_UI = os.path.join(ROOT, 'work', 'tl', 'ui.tsv')

STORY_COLS = ['key', 'file', 'en', 'ja', 'ko']
UI_COLS = ['file', 'id', 'en', 'ja', 'ko']

PENDING_MARKERS = ('<c_color=', '<c_size=')
SPECIAL_PREFIXES = ('//', '#', 'r:', 'sr:')

PH_RE = re.compile(r'\{[^{}\n]*\}')
TAG_RE = re.compile(r'<[^<>\n]+>')

LUA_SIMPLE = {'n': '\n', 't': '\t', 'r': '\r', 'a': '\a', 'b': '\b', 'f': '\f',
              'v': '\v', '\\': '\\', '"': '"', "'": "'"}
UI_SIMPLE = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}


def lua_unescape(s):
    """Lua 문자열 리터럴 내용을 실제 문자열로 복원한다."""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c != '\\' or i + 1 >= n:
            out.append(c)
            i += 1
            continue
        d = s[i + 1]
        if d in LUA_SIMPLE:
            out.append(LUA_SIMPLE[d])
            i += 2
        elif d == '\n':
            out.append('\n')
            i += 2
        elif d == '\r':
            out.append('\n')
            i += 3 if s[i + 2:i + 3] == '\n' else 2
        elif '0' <= d <= '9':
            j = i + 1
            k = j
            while k < n and k - j < 3 and '0' <= s[k] <= '9':
                k += 1
            out.append(chr(int(s[j:k])))
            i = k
        elif d == 'x' and re.match(r'[0-9a-fA-F]{2}', s[i + 2:i + 4]):
            out.append(chr(int(s[i + 2:i + 4], 16)))
            i += 4
        elif d == 'z':
            i += 2
            while i < n and s[i].isspace():
                i += 1
        elif d == 'u':
            m = re.match(r'\{([0-9a-fA-F]+)\}', s[i + 2:])
            if m:
                out.append(chr(int(m.group(1), 16)))
                i += 2 + m.end()
            else:
                out.append('\\u')
                i += 2
        else:
            # Lua에서는 오류지만 원문을 살리기 위해 그대로 둔다.
            out.append(c + d)
            i += 2
    return ''.join(out)


def ui_unescape(s):
    """UI 표의 이스케이프(\\\\ \\t \\r \\n)를 복원한다. 그 외 \\X 는 그대로 둔다."""
    out = []
    i, n = 0, len(s)
    while i < n:
        if s[i] == '\\' and i + 1 < n and s[i + 1] in UI_SIMPLE:
            out.append(UI_SIMPLE[s[i + 1]])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def at_escape(s):
    """실제 문자열을 AT 파일 한 줄 형식으로 바꾼다 (AT TextHelper 기준: 백슬래시, =, CR, LF 이스케이프)."""
    return (s.replace('\\', '\\\\').replace('=', '\\=')
             .replace('\r', '\\r').replace('\n', '\\n'))


def cell(s):
    """리포트 TSV 셀용: 줄바꿈과 탭을 제거한다."""
    return str(s).replace('\r', '\\r').replace('\n', '\\n').replace('\t', ' ')


def read_rows(path, required):
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter='\t')  # build_tl_tables.py writes QUOTE_MINIMAL
        try:
            header = next(reader)
        except StopIteration:
            return
        idx = {h.strip(): i for i, h in enumerate(header)}
        missing = [c for c in required if c not in idx]
        if missing:
            raise SystemExit(f'오류: {path} 헤더에 열 {missing} 이 없음 (헤더: {header})')
        for lineno, row in enumerate(reader, start=2):
            if not any(x.strip() for x in row):
                continue
            short = len(row) < len(header)
            vals = {c: (row[idx[c]] if idx[c] < len(row) else '') for c in required}
            yield lineno, vals, short


def check(loc, en, ko, warn):
    pe = Counter(PH_RE.findall(en))
    pk = Counter(PH_RE.findall(ko))
    if pe != pk:
        warn(loc, 'placeholder', en, ko,
             f'원문 {sorted(pe.elements())} / 번역 {sorted(pk.elements())}')
    te = sorted(TAG_RE.findall(en))
    tk = sorted(TAG_RE.findall(ko))
    if te != tk:
        warn(loc, 'tag', en, ko, f'원문 {te} / 번역 {tk}')
    ne, nk = en.count('\n'), ko.count('\n')
    if ne != nk:
        warn(loc, 'newline', en, ko, f'원문 줄바꿈 {ne}개 / 번역 {nk}개 (출력은 함)')
    if '\ufffd' in ko:
        warn(loc, 'mojibake', en, ko, '번역에 U+FFFD(깨진 문자) 포함')
    if '\\' in en or '\\' in ko:
        warn(loc, 'backslash', en, ko, '백슬래시 포함: AT 이스케이프 규칙 미확인 (그대로 출력함)')
    if '=' in en:
        warn(loc, 'eq_in_key', en, ko, "원문에 '=' 포함: 파서가 첫 '='에서 나눈다면 키가 잘림 (그대로 출력함)")


def convert(source, path, required, unesc, loc_fn):
    if not os.path.exists(path):
        raise SystemExit(f'오류: 입력 파일 없음: {path}')
    stats = Counter()
    entries = {}
    out_lines = []
    conflicts = []
    pending = []
    warnings = []

    def warn(loc, kind, en, ko, detail):
        warnings.append((source, loc, kind, en, ko, detail))

    for lineno, v, short in read_rows(path, required):
        loc = loc_fn(v)
        en_raw, ko_raw = v['en'], v['ko']
        stats['rows'] += 1
        if short:
            warn(loc, 'short_row', en_raw, ko_raw, f'{lineno}행: 열 수가 헤더보다 적음')
        if not ko_raw.strip():
            stats['skip_empty_ko'] += 1
            continue
        en, ko = unesc(en_raw), unesc(ko_raw)
        if not en.strip():
            stats['skip_empty_en'] += 1
            warn(loc, 'empty_en', en, ko, '원문이 비어 있음')
            continue
        if en == ko:
            stats['skip_same'] += 1
            continue
        if source == 'story' and any(m in en_raw for m in PENDING_MARKERS):
            stats['skip_pending'] += 1
            pending.append((loc, en_raw, ko_raw))
            continue
        if en.startswith(SPECIAL_PREFIXES):
            stats['skip_special'] += 1
            warn(loc, 'special_prefix', en, ko,
                 f'원문이 {" / ".join(SPECIAL_PREFIXES)} 중 하나로 시작 (주석/디렉티브/정규식 오인 가능), 건너뜀')
            continue
        check(loc, en, ko, warn)
        if en in entries:
            if entries[en]['ko'] == ko:
                stats['skip_dup_same'] += 1
            else:
                stats['conflict'] += 1
                conflicts.append((source, loc, en_raw, entries[en]['ko_raw'], ko_raw))
            continue
        entries[en] = {'ko': ko, 'ko_raw': ko_raw}
        out_lines.append(f'{at_escape(en)}={at_escape(ko)}')
        stats['out'] += 1

    return {'lines': out_lines, 'conflicts': conflicts, 'pending': pending,
            'warnings': warnings, 'stats': stats}


def write_text(path, lines):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        for line in lines:
            f.write(line + '\n')


def write_tsv(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\t'.join(header) + '\n')
        for r in rows:
            f.write('\t'.join(cell(x) for x in r) + '\n')


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description='TSV -> XUnity.AutoTranslator 번역 파일 변환')
    ap.add_argument('out_dir', help='출력 폴더 (없으면 만든다)')
    ap.add_argument('--story', default=DEFAULT_STORY, help='story.tsv 경로')
    ap.add_argument('--ui', default=DEFAULT_UI, help='ui.tsv 경로')
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)

    story = convert('story', args.story, STORY_COLS, lua_unescape,
                    lambda v: f"{v['file']}|{v['key']}")
    ui = convert('ui', args.ui, UI_COLS, ui_unescape,
                 lambda v: f"{v['file']}|{v['id']}")

    write_text(os.path.join(args.out_dir, 'story.txt'), story['lines'])
    write_text(os.path.join(args.out_dir, 'ui.txt'), ui['lines'])
    write_tsv(os.path.join(args.out_dir, '_conflicts.tsv'),
              ['source', 'location', 'en', 'kept_ko', 'ignored_ko'],
              story['conflicts'] + ui['conflicts'])
    write_tsv(os.path.join(args.out_dir, '_pending_tags.tsv'),
              ['location', 'en', 'ko'], story['pending'])
    all_warn = story['warnings'] + ui['warnings']
    write_tsv(os.path.join(args.out_dir, '_warnings.tsv'),
              ['source', 'location', 'kind', 'en', 'ko', 'detail'],
              [(s, l, k, at_escape(e), at_escape(ko), d) for s, l, k, e, ko, d in all_warn])

    # 요약
    kinds = Counter(w[2] for w in all_warn)
    print('== 충돌 예시 (최대 5개) ==')
    shown = (story['conflicts'] + ui['conflicts'])[:5]
    for src, loc, en_raw, kept, ign in shown:
        print(f'  [{src}] {loc}: en={cell(en_raw)}  유지={cell(kept)}  무시={cell(ign)}')
    if not shown:
        print('  (없음)')
    print('== 경고 (최대 30개 출력, 전체는 _warnings.tsv) ==')
    for src, loc, kind, en, ko, detail in all_warn[:30]:
        print(f'  [{kind}] {src} {loc}: {detail}')
    if len(all_warn) > 30:
        print(f'  ... 외 {len(all_warn) - 30}개')
    print('== 요약 ==')
    for name, res in (('story', story), ('ui', ui)):
        st = res['stats']
        print(f"  {name}: 행 {st['rows']} / 출력 {st['out']} / "
              f"건너뜀(번역 없음 {st['skip_empty_ko']}, 원문 없음 {st['skip_empty_en']}, "
              f"원문=번역 {st['skip_same']}, 태그보류 {st['skip_pending']}, "
              f"특수접두사 {st['skip_special']}, 동일중복 {st['skip_dup_same']}) / "
              f"충돌 {st['conflict']} / 경고 {len(res['warnings'])}")
    print(f"  경고 종류별: {dict(kinds)}")
    print(f"  출력 폴더: {os.path.abspath(args.out_dir)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
