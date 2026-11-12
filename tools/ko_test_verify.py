import sys, json, base64, os
import UnityPy
sys.path.insert(0, os.path.dirname(__file__))
import ff7crypt, ko_test as k

P = lambda rel: k.MD + rel.replace('/', os.sep)
idx = json.load(open(os.path.join(k.MD, 'index.json')))
c = json.loads(ff7crypt.decrypt(open(P(idx['language_catalog_en']), 'rb').read()))
for n in k.PATCH:
    e = next(x for x in c['files'] if x['name'] == n)
    d = json.loads(ff7crypt.decrypt(open(P(e['path']), 'rb').read()))
    print(n, [x['value'] for x in d['data'] if x['id'] in k.PATCH[n]])
env = UnityPy.load(k.FONT_BUNDLE)
f = [o.read() for o in env.objects if o.type.name == 'Font'][0]
print(f.m_Name, bytes(f.m_FontData[:4]), len(f.m_FontData))
cj = json.load(open(os.path.join(k.AA, 'catalog.json'), encoding='utf-8'))
s = base64.b64decode(cj['m_ExtraDataString']).decode('utf-16-le', 'ignore')
i = s.find(k.FONT_HASH)
print(s[i:i + 70])
