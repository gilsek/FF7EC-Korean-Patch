"""Dump movie (cutscene) subtitle sheets from the Octo store.

Assets live at `moviesubtitles/<category>/..._<lang>.a` (TextAsset inside the bundle).
Each sheet is a spreadsheet export:

    ## <title>
    #<comment rows>
    Time,Trim,Speaker,Text[,Position]

  * `Time`     start, in frames (no h:mm:ss values in the current data)
  * `Trim`     frames added to Time to get the erase time (end = Time + Trim)
  * `Speaker`  may be empty, may carry <i>/<size> tags
  * `Text`     in-subtitle line breaks are the two characters `\\n`; may contain commas,
               so everything between Speaker and the trailing Position belongs to Text
  * `Position` optional: bottom / center

usage: python -I dump_moviesub.py [OUT_ROOT]
  default OUT_ROOT = <repo>/work/moviesub
Writes:
  OUT_ROOT/raw/<lang>/<path under moviesubtitles, .a -> .csv>  (byte-exact TextAsset)
  OUT_ROOT/moviesub.tsv                                         (file,key,start,end,ja,en)
"""
import os, re, site, sys

sys.stdout.reconfigure(encoding='utf-8')
if sys.flags.isolated:  # python -I drops the user site dir, where pycryptodome lives
    site.addsitedir(site.getusersitepackages())

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import octo
import UnityPy

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'work', 'moviesub')
OUT = os.path.abspath(OUT)
RAW = os.path.join(OUT, 'raw')

POSITIONS = {'bottom', 'center', 'top'}
NAME_RE = re.compile(r'^moviesubtitles/(?P<path>.+)_(?P<lang>[a-z]{2})\.a$')


def sheet_text(entry, idx):
    d = idx.get(('A%d' % entry['id']).encode().hex())
    p = d and os.path.join(d, entry['md5'])
    if not p or not os.path.exists(p):
        return None
    env = UnityPy.load(octo.deobfuscate(open(p, 'rb').read(), entry['name']))
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        raw = o.read().m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8')
        return raw
    return b''


def parse_sheet(raw):
    """-> (title, [dict(start, trim, speaker, text)])"""
    s = raw.decode('utf-8', 'replace')
    title = ''
    rows = []
    for ln in s.replace('\r\n', '\n').split('\n'):
        if not ln:
            continue
        if ln.startswith('##'):
            title = ln[2:].strip()
            continue
        if ln.startswith('#'):
            continue
        f = ln.split(',')
        if len(f) < 4:
            print('  ! short row:', ln)
            continue
        pos = ''
        if f[-1].strip().lower() in POSITIONS:
            pos = f[-1].strip()
            f = f[:-1]
        rows.append({
            'start': f[0].strip(),
            'trim': f[1].strip(),
            'speaker': f[2].strip(),
            'text': ','.join(f[3:]),
            'pos': pos,
        })
    return title, rows


def cell(s):
    # newlines become the two characters \n; tabs become spaces
    return s.replace('\r', '').replace('\n', '\\n').replace('\t', ' ')


def num(v):
    try:
        return int(v)
    except ValueError:
        return None


def main():
    db = octo.load_db()
    idx = octo._bucket_index()
    files = {}
    for kind in ('assetBundleList', 'resourceList'):
        for e in db[kind]:
            m = NAME_RE.match(e['name'])
            if not m:
                continue
            files.setdefault(m.group('path'), {})[m.group('lang')] = (kind, e)
    print('assets:', sum(len(v) for v in files.values()), 'groups:', len(files))

    langs = sorted({lg for v in files.values() for lg in v})
    per_lang = {lg: 0 for lg in langs}
    parsed = {}
    for path in sorted(files):
        for lg, (kind, e) in sorted(files[path].items()):
            if kind != 'assetBundleList':
                continue
            raw = sheet_text(e, idx)
            if raw is None:
                print('  ! missing on disk:', e['name'])
                continue
            sub = os.path.join(RAW, lg, os.path.dirname(path))
            os.makedirs(sub, exist_ok=True)
            with open(os.path.join(sub, os.path.basename(path) + '_' + lg + '.csv'), 'wb') as f:
                f.write(raw)
            title, rows = parse_sheet(raw)
            parsed[(path, lg)] = (title, rows)
            per_lang[lg] = per_lang.get(lg, 0) + len(rows)

    tsv = os.path.join(OUT, 'moviesub.tsv')
    n_rows = 0
    with open(tsv, 'w', encoding='utf-8', newline='\n') as out:
        out.write('file\tkey\tstart\tend\tja\ten\n')
        for path in sorted(files):
            ja = parsed.get((path, 'ja'))
            en = parsed.get((path, 'en'))
            n = max(len(ja[1]) if ja else 0, len(en[1]) if en else 0)
            for i in range(n):
                rj = ja[1][i] if ja and i < len(ja[1]) else None
                re_ = en[1][i] if en and i < len(en[1]) else None
                base = rj or re_
                start = num(base['start'])
                trim = num(base['trim'])
                end = start + trim if start is not None and trim is not None else None
                out.write('\t'.join([
                    cell('moviesubtitles/' + path),
                    str(i + 1),
                    cell(base['start']),
                    str(end) if end is not None else '',
                    cell(rj['text']) if rj else '',
                    cell(re_['text']) if re_ else '',
                ]) + '\n')
                n_rows += 1

    print('raw dumps:', os.path.join(RAW, '<lang>'))
    print('languages:', ', '.join(f'{lg}={per_lang[lg]}' for lg in langs))
    print('tsv rows:', n_rows, '->', tsv)
    hit = any('行くぞ\u3000新入り！' in r['text'] for _, rows in parsed.values() for r in rows)
    print('verify "行くぞ\u3000新入り！":', 'FOUND' if hit else 'MISSING')
    empty = sum(1 for path in files for lg in ('ja', 'en')
                if (path, lg) in parsed and not parsed[(path, lg)][1])
    print('empty sheets:', empty)


if __name__ == '__main__':
    main()
