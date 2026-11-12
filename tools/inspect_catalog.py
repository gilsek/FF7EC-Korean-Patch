import json, os, hashlib, base64, glob, sys
sys.path.insert(0, os.path.dirname(__file__))
from ff7crypt import decrypt

G = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC"
MD = os.path.join(G, 'FF7EC_Data', 'StreamingAssets', 'MasterData')
cat = json.load(open(glob.glob('work/sa_lang_catalogs/en/F7WH*.json')[0], encoding='utf-8'))
print({k: v for k, v in cat.items() if k != 'files'}, len(cat['files']))
f = cat['files'][0]
b = open(os.path.join(MD, *f['path'].strip('/').split('/')), 'rb').read()
b32 = lambda d: base64.b32encode(d).decode().rstrip('=')
for name, data in [('enc', b), ('dec', decrypt(b))]:
    for h in ['sha256', 'sha1', 'md5']:
        print(name, h, b32(getattr(hashlib, h)(data).digest()) == f['hash'])
print('name_hash sha256(name)', b32(hashlib.sha256(f['name'].encode()).digest()) == f['name_hash'])
print('file name in path = sha256(enc)?', b32(hashlib.sha256(b).digest()), f['path'])

st = []
for p in glob.glob('work/save_localize/En/*.json'):
    j = json.load(open(p, encoding='utf-8'))
    if not isinstance(j, dict) or 'data' not in j: print('nodata', os.path.basename(p), str(j)[:150]); continue
    st.append((sum(len(e.get('value', '')) for e in j['data']), len(j['data']), os.path.basename(p)))
for s in sorted(st, reverse=True)[:30]:
    print(s)
