"""Build a subset GalTransl project with the gt_project_ui_v2 rows whose English source contains an
en-glossary key but whose Korean output lacks the glossary Korean. -> work/gt_ui_en_retr (+ rows.json map)
usage: python -I tools/ui_en_retr_build.py"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = os.path.join(B, 'gt_project_ui_v2'); W = os.path.join(B, 'work', 'gt_ui_en_retr')
SKIP = {'Huge Mega Watermelon', 'Huge Materia'}  # pending user decision on 휴지
G = collections.defaultdict(set)
for l in open(os.path.join(P, 'Dict', 'gpt_dict_en.txt'), encoding='utf-8'):
    t = l.rstrip('\n').split('\t')
    if len(t) >= 2 and not l.startswith('#') and t[0] not in SKIP: G[t[0]].add(t[1])
RX = {e: re.compile(r'\b' + re.escape(e) + r'(s|es)?\b') for e in G}
sq = lambda s: s.replace(' ', '')
if os.path.exists(W): sys.exit('exists: ' + W)
os.makedirs(os.path.join(W, 'gt_input'))
for f in ['config.yaml', 'name替换表.csv', 'translation_guideline.md']:
    if os.path.exists(os.path.join(P, f)): shutil.copy2(os.path.join(P, f), W)
shutil.copytree(os.path.join(P, 'Dict'), os.path.join(W, 'Dict'))
rows, by = [], collections.Counter()
for p in sorted(glob.glob(os.path.join(P, 'gt_input', '*.json'))):
    f = os.path.basename(p); I = json.load(open(p, encoding='utf-8'))
    O = json.load(open(os.path.join(P, 'gt_output', f), encoding='utf-8')); sub = []
    for i, (a, b) in enumerate(zip(I, O)):
        bad = [e for e, r in RX.items() if r.search(a['message']) and not any(sq(k) in sq(b['message']) for k in G[e])]
        if bad:
            sub.append(a); rows.append({'file': f, 'idx': i, 'keys': bad, 'old': b['message']}); by.update(bad)
    if sub: json.dump(sub, open(os.path.join(W, 'gt_input', f), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(rows, open(os.path.join(W, 'rows.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('rows', len(rows), 'files', len(set(r['file'] for r in rows))); print(by.most_common(15))
