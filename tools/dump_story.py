"""Extract story text tables (TXT_xxx = "...") from en/ja Lua script bundles in the Octo store.
usage: python dump_story.py OUT_DIR [lang]
Writes OUT_DIR/<lang>/<bundle name>.tsv (key<TAB>text, text JSON-escaped) and prints stats."""
import json, os, re, sys
import UnityPy
sys.path.insert(0, os.path.dirname(__file__))
import octo

out, lang = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else 'en')
LINE = re.compile(r'^\s*(TXT_[A-Za-z0-9_]+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.M)
db = octo.load_db()
idx = octo._bucket_index()
stats = {}
seen_keys = {}
for e in db['assetBundleList']:
    name = e['name']
    if f'/{lang}/' not in name or 'luascript' not in name:
        continue
    d = idx.get(('A%d' % e['id']).encode().hex())
    p = d and os.path.join(d, e['md5'])
    if not p or not os.path.exists(p):
        continue
    env = UnityPy.load(octo.deobfuscate(open(p, 'rb').read(), name))
    rows = []
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        t = o.read()
        s = t.m_Script
        if isinstance(s, bytes):
            s = s.decode('utf-8', 'replace')
        for k, v in LINE.findall(s):
            rows.append((k, v))
    if not rows:
        continue
    cat = name.split('/')[1]
    st = stats.setdefault(cat, [0, 0, 0])
    st[0] += 1; st[1] += len(rows)
    st[2] += sum(len(v) for _, v in rows)
    for k, v in rows:
        seen_keys[k] = v
    q = os.path.join(out, lang, name + '.tsv')
    os.makedirs(os.path.dirname(q), exist_ok=True)
    with open(q, 'w', encoding='utf-8') as f:
        for k, v in rows:
            f.write(f'{k}\t{v}\n')
for k, v in stats.items():
    print(f'{k}: bundles={v[0]} lines={v[1]} chars={v[2]}')
u = set(seen_keys.values())
print('unique keys', len(seen_keys), 'unique texts', len(u), 'chars', sum(map(len, u)), 'words', sum(len(x.split()) for x in u))
