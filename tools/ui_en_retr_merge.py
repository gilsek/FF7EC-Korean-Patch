"""Merge work/gt_ui_en_retr/gt_output back into gt_project_ui_v2/gt_output. A row is taken only if
the project row is still the old text, tags/newlines match the source, and the glossary key now hits.
Backup in gt_project_ui_v2/review/_retr_backup. usage: python -I tools/ui_en_retr_merge.py [--dry]"""
import json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = os.path.join(B, 'gt_project_ui_v2'); W = os.path.join(B, 'work', 'gt_ui_en_retr')
DRY = '--dry' in sys.argv
TAG = re.compile(r'<[^<>\n]+>'); VAR = re.compile(r'\{\d+\}')
G = collections.defaultdict(set)
for l in open(os.path.join(P, 'Dict', 'gpt_dict_en.txt'), encoding='utf-8'):
    t = l.rstrip('\n').split('\t')
    if len(t) >= 2 and not l.startswith('#'): G[t[0]].add(t[1])
sq = lambda s: s.replace(' ', '')
rows = json.load(open(os.path.join(W, 'rows.json'), encoding='utf-8'))
pos = collections.Counter(); NEW = {}; st = collections.Counter(); out = {}; bad = []
for r in rows:
    f = r['file']
    if f not in NEW: NEW[f] = json.load(open(os.path.join(W, 'gt_output', f), encoding='utf-8'))
    n = NEW[f][pos[f]]; pos[f] += 1
    if f not in out: out[f] = json.load(open(os.path.join(P, 'gt_output', f), encoding='utf-8'))
    src = json.load(open(os.path.join(P, 'gt_input', f), encoding='utf-8'))[r['idx']]['message']
    m = n['message']
    if out[f][r['idx']]['message'] != r['old']: st['changed_since'] += 1; continue
    if TAG.findall(m) != TAG.findall(src) or sorted(VAR.findall(m)) != sorted(VAR.findall(src)) or m.count('\n') != src.count('\n'):
        st['tag_or_nl'] += 1; bad.append((f, r['idx'], m[:60])); continue
    if not all(any(sq(k) in sq(m) for k in G[e]) for e in r['keys']): st['still_missing'] += 1; bad.append((f, r['idx'], m[:60])); continue
    out[f][r['idx']]['message'] = m; st['merged'] += 1
print(dict(st), 'DRY' if DRY else '')
for x in bad[:25]: print('SKIP', x)
if not DRY:
    bk = os.path.join(P, 'review', '_retr_backup'); os.makedirs(bk, exist_ok=True)
    for f, d in out.items():
        if not os.path.exists(os.path.join(bk, f)): shutil.copy2(os.path.join(P, 'gt_output', f), os.path.join(bk, f))
        json.dump(d, open(os.path.join(P, 'gt_output', f), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
