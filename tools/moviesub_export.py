"""Export movie-subtitle TSV rows to GalTransl input JSON (one file per cutscene).

usage: python -I tools/moviesub_export.py [PROJECT_DIR]
  default PROJECT_DIR = <repo>/gt_project_movie

Input : work/moviesub/moviesub.tsv  (file,key,start,end,ja,en; tab separated,
        in-subtitle line breaks are the two characters \\n)
        work/moviesub/raw/ja/<path>_ja.csv (Time,Trim,Speaker,Text[,Position])
Output: PROJECT_DIR/gt_input/<file with / -> __>.json  as [{"name": ..., "message": ...}]
        - message keeps the two characters \\n replaced by a real newline
        - name comes from the Speaker column of the same row in the raw ja sheet
          (tags such as <i> are stripped); empty when the sheet/row is missing
        - rows whose ja is empty are skipped, but the remaining rows keep their order
          so translation output lines map 1:1 onto the TSV rows with non-empty ja
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TSV = os.path.join(ROOT, 'work', 'moviesub', 'moviesub.tsv')
RAW_JA = os.path.join(ROOT, 'work', 'moviesub', 'raw', 'ja')
POSITIONS = {'bottom', 'center', 'top'}
TAG = re.compile(r'<[^<>]*>')


def read_tsv():
    with open(TSV, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def speakers_for(file_rel):
    """-> {key(int): speaker} from the raw ja sheet, or {} if unavailable."""
    path = os.path.join(RAW_JA, file_rel + '_ja.csv')
    if not os.path.exists(path):
        return {}
    text = open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    out = {}
    i = 0
    for ln in text.split('\n'):
        if not ln or ln.startswith('#'):
            continue
        f = ln.split(',')
        if len(f) < 4:
            continue
        if f[-1].strip().lower() in POSITIONS:
            f = f[:-1]
        i += 1
        out[i] = TAG.sub('', f[2]).strip()
    return out


def json_name(file_rel):
    return file_rel.replace('/', '__') + '.json'


def main():
    proj = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, 'gt_project_movie')
    outdir = os.path.join(proj, 'gt_input')
    os.makedirs(outdir, exist_ok=True)
    rows = read_tsv()

    # group TSV rows by cutscene, keep file order stable
    files = {}
    for r in rows:
        files.setdefault(r['file'], []).append(r)

    written = skipped = no_speaker = 0
    for file_rel, group in files.items():
        spk = speakers_for(file_rel.replace('moviesubtitles/', '', 1))
        entries = []
        for r in group:
            ja = r['ja']
            if not ja.strip():
                skipped += 1
                continue
            try:
                keyno = int(r['key'])
            except ValueError:
                keyno = -1
            name = spk.get(keyno, '')
            if not name:
                no_speaker += 1
            entries.append({'name': name, 'message': ja.replace('\\n', '\n')})
        if not entries:
            continue
        with open(os.path.join(outdir, json_name(file_rel)), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.write('\n')
        written += 1

    print('input json files:', written, '->', outdir)
    print('messages:', sum(1 for r in rows if r['ja'].strip()), 'skipped empty ja:', skipped,
          'rows without speaker:', no_speaker)


if __name__ == '__main__':
    main()
