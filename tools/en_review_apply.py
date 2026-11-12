"""Apply Haiku review suggestions to gt_project_ui_v2 conservatively.
Chunk items (file/idx) and dedup items (no -> every row with the same en/ko text).
Accepted: suggestion adds a glossary term, or type in format/unnatural/mistranslation(dedup only),
or (file,idx) in ACCEPT. Always: current must still match (after en_name_fix normalization),
tag sequence and newline count must be unchanged. Backup in review/_apply_backup.
usage: python -I tools/en_review_apply.py [--dry] [-v]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'gt_project_ui_v2')
DRY = '--dry' in sys.argv; V = '-v' in sys.argv
src = open(os.path.join(HERE, 'en_name_fix.py'), encoding='utf-8').read()
ns = {'re': re}; exec(src[src.index('FIX = ['):src.index('bk = ')], ns); FIX = ns['FIX']
def nf(en, m):
    for e, k, r in FIX:
        if e.search(en): m = k.sub(r, m)
    return m
ACCEPT = {('ui__HelpPopup.json', 22), ('ui__StoreProduct__001.json', 153)}
DENY = {('ui__Item__003.json', 466), ('ui__HomeBackground.json', 64), ('ui__Mission__002.json', 326), ('ui__Shop.json', 177)}
TAG = re.compile(r'<[^<>\n]+>')
G = set()
for l in open(os.path.join(ROOT, 'Dict', 'gpt_dict.txt'), encoding='utf-8'):
    t = l.rstrip('\n').split('\t')
    if len(t) >= 2 and not l.startswith('#') and len(t[1]) >= 2: G.add(t[1])
IN, OUT = {}, {}
for p in glob.glob(os.path.join(ROOT, 'gt_output', '*.json')):
    b = os.path.basename(p)
    IN[b] = json.load(open(os.path.join(ROOT, 'gt_input', b), encoding='utf-8'))
    OUT[b] = json.load(open(p, encoding='utf-8'))
U = lambda s: s.replace('⏎', '\n')
st = collections.Counter(); changed = set()
def ok(x, c, s, dedup):
    if TAG.findall(c) != TAG.findall(s) or c.count('\n') != s.count('\n'): return 'tagdiff'
    if any(t in c and t not in s for t in G): return 'dropsgloss'
    if any(t in s and t not in c for t in G): return None
    if x['type'] in ('format', 'unnatural') or (dedup and x['type'] == 'mistranslation'): return None
    return 'notaccepted'
def apply(f, i, x, dedup):
    en = IN[f][i]['message']; cur = OUT[f][i]['message']
    c = nf(en, U(x.get('current', ''))); s = nf(en, U(x['suggestion']))
    if c == s or cur == s: st['noop'] += 1; return
    if cur != c: st['stale'] += 1; return
    r = 'deny' if (f, i) in DENY else None if (f, i) in ACCEPT else ok(x, c, s, dedup)
    if r: st[r + '_' + x['severity']] += 1; return
    st['apply_' + x['severity']] += 1
    if V: print(f, i, repr(c[:70]), '->', repr(s[:70]))
    OUT[f][i]['message'] = s; changed.add(f)
for p in sorted(glob.glob(os.path.join(ROOT, 'review', 'haiku', 'chunk_*.json'))):
    for x in json.load(open(p, encoding='utf-8')):
        f, i = x.get('file'), x.get('idx')
        if f in OUT and isinstance(i, int) and i < len(OUT[f]): apply(f, i, x, False)
        else: st['badref'] += 1
ALL = [(f, i, a['message']) for f in OUT for i, a in enumerate(IN[f])]
def apply_sub(f, i, x):  # dedup items are sentence-level: replace the sentence inside the row
    en = IN[f][i]['message']; cur = OUT[f][i]['message']
    c = nf(en, U(x.get('current', ''))); s = nf(en, U(x['suggestion']))
    if c == s or (s in cur and c not in cur): st['noop'] += 1; return
    if not c or c not in cur: st['stale'] += 1; return
    r = 'deny' if (f, i) in DENY else ok(x, c, s, True)
    if r: st[r + '_' + x['severity']] += 1; return
    st['apply_' + x['severity']] += 1
    new = cur.replace(c, s)
    if V: print(f, i, repr(c[:70]), '->', repr(s[:70]))
    OUT[f][i]['message'] = new; changed.add(f)
for p in sorted(glob.glob(os.path.join(ROOT, 'review', 'haiku', 'dedup_*.json'))):
    D = {}
    for l in open(os.path.join(ROOT, 'review', 'dedup', os.path.basename(p)[6:-5] + '.txt'), encoding='utf-8'):
        t = l.rstrip('\n').split('\t')
        if len(t) == 3 and t[0].isdigit(): D[int(t[0])] = U(t[1])
    for x in json.load(open(p, encoding='utf-8')):
        k = D.get(x.get('no'))
        rows = [(f, i) for f, i, m in ALL if k and k in m]
        if not rows: st['dedup_unmatched'] += 1; continue
        for f, i in rows: apply_sub(f, i, x)
bk = os.path.join(ROOT, 'review', '_apply_backup')
if not DRY:
    os.makedirs(bk, exist_ok=True)
    for f in changed:
        if not os.path.exists(os.path.join(bk, f)):
            shutil.copy2(os.path.join(ROOT, 'gt_output', f), os.path.join(bk, f))
        json.dump(OUT[f], open(os.path.join(ROOT, 'gt_output', f), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(sorted(st.items())), 'files', len(changed), 'DRY' if DRY else '')
