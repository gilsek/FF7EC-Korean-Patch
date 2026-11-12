"""Dump full Lua script TextAssets (m_Script) from en/ja luascript bundles in the Octo store.
usage: python dump_lua_full.py OUT_DIR [lang] [map_regex]
  lang       en (default) or ja
  map_regex  optional regex on bundle name, e.g. "luascript/(0001|0002)/"
Writes OUT_DIR/<bundle name>.lua (raw script text, UTF-8) for each TextAsset whose name is in the bundle.
Also writes OUT_DIR/_other/<bundle name>.<objname>.lua for non-script TextAssets with a different name.
Prints stats."""
import os, re, sys
import UnityPy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import octo

out = sys.argv[1]
lang = sys.argv[2] if len(sys.argv) > 2 else 'en'
map_rx = re.compile(sys.argv[3]) if len(sys.argv) > 3 else None

db = octo.load_db()
idx = octo._bucket_index()
n_bundles = 0
n_texts = 0
n_bytes = 0
type_counts = {}
for e in db['assetBundleList']:
    name = e['name']
    if f'/{lang}/' not in name or 'luascript' not in name:
        continue
    if map_rx and not map_rx.search(name):
        continue
    d = idx.get(('A%d' % e['id']).encode().hex())
    p = d and os.path.join(d, e['md5'])
    if not p or not os.path.exists(p):
        continue
    env = UnityPy.load(octo.deobfuscate(open(p, 'rb').read(), name))
    wrote = False
    for o in env.objects:
        type_counts[o.type.name] = type_counts.get(o.type.name, 0) + 1
        if o.type.name != 'TextAsset':
            continue
        t = o.read()
        s = t.m_Script
        if isinstance(s, bytes):
            s = s.decode('utf-8', 'replace')
        # one bundle holds several TextAssets (one per script); file them under <bundle>/<object name>
        objname = (getattr(t, 'm_Name', '') or f'object_{o.path_id}').strip()
        objname = re.sub(r'[\\/:*?"<>|]', '_', objname)
        if not objname.endswith('.lua'):
            objname += '.lua'
        q = os.path.join(out, name, objname)
        os.makedirs(os.path.dirname(q), exist_ok=True)
        with open(q, 'w', encoding='utf-8', newline='\n') as f:
            f.write(s)
        n_texts += 1
        n_bytes += len(s.encode('utf-8'))
        wrote = True
    if wrote:
        n_bundles += 1
print(f'bundles={n_bundles} textassets={n_texts} bytes={n_bytes}')
print('object types seen:', sorted(type_counts.items(), key=lambda x: -x[1])[:20])
