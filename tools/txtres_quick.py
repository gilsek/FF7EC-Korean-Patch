"""Heuristic TxtRes reader for FF7 Rebirth zen packages: finds ASCII FString keys starting with '$'
and reads the FString that follows (UTF-16 when length<0). Pairs JP/KR by (file, key, occurrence).
usage: python txtres_quick.py <Text dir with JP/KR> <out.tsv>"""
import os, re, struct, sys, csv

def fstr(d, i):
    n = struct.unpack_from('<i', d, i)[0]
    if n > 0 and n < 4096:
        s = d[i+4:i+4+n]
        if s[-1:] != b'\0': return None, i
        return s[:-1].decode('latin-1'), i + 4 + n
    if n < 0 and -n < 20000:
        s = d[i+4:i+4-2*n]
        if s[-2:] != b'\0\0': return None, i
        return s[:-2].decode('utf-16-le', 'replace'), i + 4 - 2*n
    if n == 0: return '', i + 4
    return None, i

KEY = re.compile(rb'\$[\x21-\x7e]{1,200}\x00')
def parse(path):
    d = open(path, 'rb').read(); out = []; seen = {}
    for m in KEY.finditer(d):
        i = m.start() - 4
        if i < 0 or struct.unpack_from('<i', d, i)[0] != len(m.group()): continue
        key = m.group()[:-1].decode()
        val, _ = fstr(d, m.end())
        if val is None: continue
        k = seen.get(key, 0); seen[key] = k + 1
        out.append((key, k, val))
    return out

def esc(s): return s.replace('\\', '\\\\').replace('\t', '\\t').replace('\r', '').replace('\n', '\\n')

root, dst = sys.argv[1], sys.argv[2]
tab = {}
for L in ('JP', 'KR'):
    for f in sorted(os.listdir(os.path.join(root, L))):
        if not f.endswith('.uasset'): continue
        for key, k, v in parse(os.path.join(root, L, f)):
            tab.setdefault((f, key, k), {})[L] = v
both = sum(1 for v in tab.values() if len(v) == 2)
print('entries', len(tab), 'paired', both, 'jp-only', sum(1 for v in tab.values() if set(v) == {'JP'}), 'kr-only', sum(1 for v in tab.values() if set(v) == {'KR'}))
with open(dst, 'w', encoding='utf-8', newline='') as fo:
    w = csv.writer(fo, delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_NONE, escapechar=None, quotechar='\x01')
    w.writerow(['file', 'key', 'occ', 'jp', 'kr'])
    for (f, key, k), v in sorted(tab.items()):
        w.writerow([f, key, k, esc(v.get('JP', '')), esc(v.get('KR', ''))])
