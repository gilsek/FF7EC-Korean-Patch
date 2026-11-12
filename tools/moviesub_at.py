"""Build an XUnity.AutoTranslator text file from the movie-subtitle translation project.

usage: python -I tools/moviesub_at.py [PROJECT_DIR] [--out PATH]
  default PROJECT_DIR = <repo>/gt_project_movie
  default OUT         = <repo>/work/moviesub/zz_moviesub.txt

Pairs gt_output/<file>.json with the TSV rows that moviesub_export.py turned into
gt_input (same order, empty-ja rows skipped) and writes one line per message:

    <ja original>=<korean translation>

* in-subtitle line breaks are the two characters \\n on both sides
* '=' is escaped as '\\=' on both sides
* a second key with the \\n sequences removed is added when it differs from the original
* duplicate keys are dropped (first translation wins); conflicts are counted

Output is UTF-8 without BOM, LF line endings, no trailing spaces.
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TSV = os.path.join(ROOT, 'work', 'moviesub', 'moviesub.tsv')


def json_name(file_rel):
    return file_rel.replace('/', '__') + '.json'


def esc(s):
    return s.replace('=', '\\=')


def clean(s):
    """The model sometimes splits a line with <br> although the source had no tag;
    AutoTranslator would print it literally, so turn it into a plain space."""
    return re.sub(r'<\s*br\s*/?\s*>', ' ', s, flags=re.I)


def main():
    args = sys.argv[1:]
    out = os.path.join(ROOT, 'work', 'moviesub', 'zz_moviesub.txt')
    if '--out' in args:
        i = args.index('--out')
        out = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    proj = os.path.abspath(args[0]) if args else os.path.join(ROOT, 'gt_project_movie')

    with open(TSV, encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))

    files = {}
    for r in rows:
        files.setdefault(r['file'], []).append(r)

    lines = []
    seen = {}
    conflicts = empties = newline_mismatch = missing_files = 0
    ref_line = None
    for file_rel, group in files.items():
        src_rows = [r for r in group if r['ja'].strip()]
        path = os.path.join(proj, 'gt_output', json_name(file_rel))
        if not os.path.exists(path):
            missing_files += 1
            continue
        dst = json.load(open(path, encoding='utf-8'))
        if len(dst) != len(src_rows):
            print('! count mismatch', file_rel, len(src_rows), len(dst))
        for r, d in zip(src_rows, dst):
            src_expected = r['ja'].replace('\\n', '\n')
            ko = clean((d.get('message') or '').replace('\r\n', '\n').replace('\r', '\n'))
            if not ko.strip():
                empties += 1
                continue
            if ko.count('\n') != src_expected.count('\n'):
                newline_mismatch += 1
            key = r['ja']
            val = ko.replace('\n', '\\n')
            pairs = [(key, val)]
            key_nn = key.replace('\\n', '')
            if key_nn != key:
                pairs.append((key_nn, val))
            for k, v in pairs:
                k2, v2 = esc(k), esc(v)
                if k2 in seen:
                    if seen[k2] != v2:
                        conflicts += 1
                    continue
                seen[k2] = v2
                lines.append(k2 + '=' + v2)
            if key == '行くぞ　新入り！':
                ref_line = (key, val)

    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print('output:', out)
    print('lines:', len(lines), 'unique keys:', len(seen),
          'newline-free variants:', sum(1 for l in lines if '\\n' not in l.split('=', 1)[0]))
    print('missing output files:', missing_files, 'empty translations:', empties,
          'newline mismatches:', newline_mismatch, 'key conflicts:', conflicts)
    if ref_line:
        print('reference line: %s=%s' % ref_line)
    else:
        print('reference line: NOT FOUND (行くぞ　新入り！)')


if __name__ == '__main__':
    main()
