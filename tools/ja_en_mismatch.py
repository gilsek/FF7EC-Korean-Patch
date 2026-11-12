"""Find UI entries whose en-source translation and ja-source translation disagree (like 전하 vs 대전).
Short names only (<= 25 chars of Korean), since long sentences differ naturally.
Output: work/opus_review/ja_en_mismatch.tsv (file, id, ja, en, ko_from_ja, ko_from_en)
usage: python -I tools/ja_en_mismatch.py"""
import csv, os, re, sys
csv.field_size_limit(10**9); sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
def norm(s): return re.sub(r'[\s·・.\-]', '', re.sub(r'<[^>]+>', '', s))
ja = {}
for r in csv.DictReader(open(os.path.join(B, 'work/tl_ui_ja/ui_ja_ko.tsv'), encoding='utf-8'), delimiter='\t'):
    ja[(r['file'], r['id'])] = r
out = []; seen = set()
for r in csv.DictReader(open(os.path.join(B, 'work/tl_ui_v2/ui_ko.tsv'), encoding='utf-8'), delimiter='\t'):
    j = ja.get((r['file'], r['id']))
    if not j or not j['ko'] or not r['ko']: continue
    a, b = j['ko'], r['ko']
    if len(a) > 25 or len(b) > 25 or '\\n' in a: continue
    if norm(a) == norm(b): continue
    k = (j['ja'], r['en'], a, b)
    if k in seen: continue
    seen.add(k); out.append((r['file'], r['id']) + k)
with open(os.path.join(B, 'work/opus_review/ja_en_mismatch.tsv'), 'w', encoding='utf-8') as f:
    for x in out: f.write('\t'.join(s.replace('\t', ' ') for s in x) + '\n')
print(len(out))
