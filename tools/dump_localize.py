"""Decrypt every file under SRC into DST (same relative paths). Reports stats.
usage: python dump_localize.py SRC DST"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from ff7crypt import decrypt

src, dst = sys.argv[1], sys.argv[2]
files = entries = chars = fails = 0
for root, _, names in os.walk(src):
    for n in names:
        p = os.path.join(root, n)
        rel = os.path.relpath(p, src)
        try:
            out = decrypt(open(p, 'rb').read())
        except Exception as e:
            fails += 1
            print('FAIL', rel, e)
            continue
        q = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(q), exist_ok=True)
        files += 1
        try:
            j = json.loads(out)
            json.dump(j, open(q, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            for e in j.get('data', []) if isinstance(j, dict) else []:
                if isinstance(e, dict) and isinstance(e.get('value'), str):
                    entries += 1
                    chars += len(e['value'])
        except ValueError:
            open(q + '.raw', 'wb').write(out)
print(f'files={files} fails={fails} text_entries={entries} chars={chars}')
