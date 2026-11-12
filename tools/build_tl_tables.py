"""Build translation source tables.
  work/tl/story.tsv : key, file, en, ja, ko   (dialogue order, first occurrence of each key)
  work/tl/ui.tsv    : file, id, en, ja, ko    (server LocalizeText En = newest; ja from built-in assets)
Text cells are kept exactly as in source (story: Lua-escaped, e.g. literal \\n; ui: JSON value with
newlines/tabs escaped as \\n / \\t). ko column is empty."""
import csv, glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import ff7crypt

ROOT = os.path.join(os.path.dirname(__file__), '..')
G = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC"
MD = G + r"\FF7EC_Data\StreamingAssets\MasterData"
OUT = os.path.join(ROOT, 'work', 'tl')
os.makedirs(OUT, exist_ok=True)


def esc(s):
    return s.replace('\\', '\\\\').replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n')


def read_story(lang):
    rows = []
    base = os.path.join(ROOT, 'work', 'story', lang)
    for p in sorted(glob.glob(os.path.join(base, '**', '*.tsv'), recursive=True)):
        rel = os.path.relpath(p, base).replace('\\', '/')[:-4]
        for line in open(p, encoding='utf-8'):
            k, v = line.rstrip('\n').split('\t', 1)
            rows.append((k, rel, v))
    return rows


def story():
    ja = {}
    for k, _, v in read_story('ja'):
        ja.setdefault(k, v)
    seen = set()
    n = 0
    with open(os.path.join(OUT, 'story.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(['key', 'file', 'en', 'ja', 'ko'])
        for k, rel, v in read_story('en'):
            if k in seen:
                continue
            seen.add(k)
            w.writerow([k, rel.replace('/en/', '/'), v, ja.get(k, ''), ''])
            n += 1
    print('story rows', n, 'missing ja', sum(1 for k in seen if k not in ja))


def ja_ui():
    """Server-side LocalizeText\\Ja (complete), falling back to built-in StreamingAssets ja (partial)."""
    out = ja_ui_builtin()
    for p in glob.glob(G + r"\save\LocalizeText\Ja\*.json"):
        name = os.path.basename(p)[:-5]
        if name == 'text_catalog':
            continue
        d = json.loads(ff7crypt.decrypt(open(p, 'rb').read()))
        out.setdefault(name, {}).update({str(x['id']): x['value'] for x in d.get('data', [])})
    return out


def ja_ui_builtin():
    idx = json.load(open(os.path.join(ROOT, 'backup', 'orig', '02_index.json'), encoding='utf-8'))
    cat = json.loads(ff7crypt.decrypt(open(MD + idx['language_catalog_ja'].replace('/', '\\'), 'rb').read()))
    out = {}
    for e in cat['files']:
        p = MD + e['path'].replace('/', '\\')
        if os.path.exists(p):
            d = json.loads(ff7crypt.decrypt(open(p, 'rb').read()))
            out[e['name']] = {str(x['id']): x['value'] for x in d.get('data', [])}
    return out


def ui():
    ja = ja_ui()
    src = G + r"\save\LocalizeText\En"
    n = miss = 0
    with open(os.path.join(OUT, 'ui.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(['file', 'id', 'en', 'ja', 'ko'])
        for p in sorted(glob.glob(src + r"\*.json")):
            name = os.path.basename(p)[:-5]
            if name == 'text_catalog':
                continue
            d = json.loads(ff7crypt.decrypt(open(p, 'rb').read()))
            jd = ja.get(name, {})
            for x in d.get('data', []):
                j = jd.get(str(x['id']))
                miss += j is None
                w.writerow([name, x['id'], esc(x['value']), esc(j or ''), ''])
                n += 1
    print('ui rows', n, 'missing ja', miss)


if __name__ == '__main__':
    story()
    ui()
