"""Apply Haiku review suggestions to gt_project_ui_ja conservatively (same gate as en_review_apply):
glossary-backed term changes, format/unnatural fixes, or (file,idx) in ACCEPT; never drop a glossary
term; tags/newlines unchanged; current must still match. Backup review/_apply_backup.
usage: python -I tools/ja_review_apply.py [--dry] [-v]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_ui_ja')
DRY = '--dry' in sys.argv; V = '-v' in sys.argv
ACCEPT = set()
DENY = {('ui_ja__006.json', 404), ('ui_ja__010.json', 184), ('ui_ja__010.json', 0), ('ui_ja__010.json', 1)}
TAG = re.compile(r'<[^<>\n]+>')
G = set()
for l in open(os.path.join(ROOT, 'Dict', 'gpt_dict.txt'), encoding='utf-8'):
    t = l.rstrip('\n').split('\t')
    if len(t) >= 2 and not l.startswith('#') and len(t[1]) >= 2: G.add(t[1])
OUT = {os.path.basename(p): json.load(open(p, encoding='utf-8')) for p in glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))}
U = lambda s: s.replace('⏎', '\n')
st = collections.Counter(); changed = set()
for p in sorted(glob.glob(os.path.join(ROOT, 'review', 'haiku', '*.json'))):
    for x in json.load(open(p, encoding='utf-8')):
        f = x.get('file')
        try: i = int(x.get('idx'))
        except Exception: st['badref'] += 1; continue
        if f not in OUT or i >= len(OUT[f]): st['badref'] += 1; continue
        cur = OUT[f][i]['message']; c = U(x.get('current', '')); s = U(x['suggestion'])
        if c == s or (s in cur and c not in cur): st['noop'] += 1; continue
        if not c or c not in cur: st['stale'] += 1; continue
        if (f, i) in DENY: st['deny'] += 1; continue
        if TAG.findall(c) != TAG.findall(s) or c.count('\n') != s.count('\n'): r = 'tagdiff'
        elif any(t in c and t not in s for t in G): r = 'dropsgloss'
        elif (f, i) in ACCEPT or any(t in s and t not in c for t in G) or x['type'] in ('format', 'unnatural'): r = None
        else: r = 'notaccepted'
        if r: st[r + '_' + x['severity']] += 1; continue
        st['apply_' + x['severity']] += 1
        if V: print(f, i, x['type'], repr(c[:60]), '->', repr(s[:60]))
        OUT[f][i]['message'] = cur.replace(c, s, 1); changed.add(f)
if not DRY:
    bk = os.path.join(ROOT, 'review', '_apply_backup'); os.makedirs(bk, exist_ok=True)
    for f in changed:
        if not os.path.exists(os.path.join(bk, f)): shutil.copy2(os.path.join(ROOT, 'gt_output', f), os.path.join(bk, f))
        json.dump(OUT[f], open(os.path.join(ROOT, 'gt_output', f), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(sorted(st.items())), 'files', len(changed), 'DRY' if DRY else '')
