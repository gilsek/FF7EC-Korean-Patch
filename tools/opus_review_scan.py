"""Collect suspicious rows for a manual (Opus) cross-review, since Gemini quota is exhausted.
Checks: numbers/variables mismatch, same source -> different translation, length ratio outliers,
leftover Latin words (ja source) / leftover kana. Writes work/opus_review/<proj>_<check>.tsv
usage: python -I tools/opus_review_scan.py"""
import glob, json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); OUT = os.path.join(B, 'work', 'opus_review')
os.makedirs(OUT, exist_ok=True)
TAG = re.compile(r'<[^<>\n]+>'); VAR = re.compile(r'\{\d+\}|%[ds]|\[[A-Za-z_]+\]')
NUM = re.compile(r'\d+(?:[.,]\d+)*')
Z = str.maketrans('０１２３４５６７８９', '0123456789')
def nums(s): return sorted(n.replace(',', '') for n in NUM.findall(TAG.sub('', s).translate(Z)))
for proj in ('gt_project_ui_ja', 'gt_project_ui_v2', 'gt_project_v2'):
    rows = []
    for p in sorted(glob.glob(os.path.join(B, proj, 'gt_input', '*.json'))):
        f = os.path.basename(p)
        I = json.load(open(p, encoding='utf-8')); O = json.load(open(os.path.join(B, proj, 'gt_output', f), encoding='utf-8'))
        rows += [(f, i, a['message'], b['message']) for i, (a, b) in enumerate(zip(I, O))]
    res = collections.defaultdict(list)
    by_src = collections.defaultdict(collections.Counter)
    for f, i, s, k in rows:
        if s == k: continue
        if sorted(VAR.findall(s)) != sorted(VAR.findall(k)): res['var'].append((f, i, s, k))
        elif nums(s) != nums(k) and not re.search(r'[一二三四五六七八九十百千万]', s): res['num'].append((f, i, s, k))
        ps, pk = len(TAG.sub('', s)), len(TAG.sub('', k))
        if ps >= 6 and (pk > ps * (3.2 if proj != 'gt_project_ui_v2' else 1.6) or pk < ps * (0.35 if proj != 'gt_project_ui_v2' else 0.12)): res['len'].append((f, i, s, k))
        if re.search(r'[぀-ヿ]', TAG.sub('', k).replace('・', '').replace('ー', '')): res['kana'].append((f, i, s, k))
        if proj != 'gt_project_ui_v2':
            lat = set(re.findall(r'[A-Za-z]{4,}', TAG.sub('', k))) - set(re.findall(r'[A-Za-z]{4,}', s))
            if lat - {'GIL', 'WAVE', 'SOLDIER'}: res['latin'].append((f, i, s, k))
        by_src[s][k] += 1
    for s, c in by_src.items():
        if len(c) > 1:
            for k, n in c.items(): res['dup'].append(('', n, s, k))
    for ck, L in res.items():
        with open(os.path.join(OUT, f'{proj}_{ck}.tsv'), 'w', encoding='utf-8') as fh:
            for f, i, s, k in L: fh.write(f'{f}\t{i}\t' + s.replace('\n', '⏎').replace('\t', ' ') + '\t' + k.replace('\n', '⏎').replace('\t', ' ') + '\n')
    print(proj, {k: len(v) for k, v in res.items()}, 'dup sources', sum(1 for c in by_src.values() if len(c) > 1))
