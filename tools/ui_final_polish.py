"""Opus cross-review fixes (Gemini quota exhausted):
1) particle after a number (배틀 2</color>을 -> 를): Korean reading of the last digit, skipped when the
   number follows Latin letters (EP3를 reads as 쓰리);  2) lowercase planet -> 별 (en source).
Backup in <proj>/review/_polish_backup.  usage: python -I tools/ui_final_polish.py [--dry]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); DRY = '--dry' in sys.argv
NO = set('2459')  # 이 사 오 구: no final consonant
P = re.compile(r'(?<![A-Za-z.])(\d+)((?:</?[a-z_]+(?:=[^>]*)?>|[”」』"])*)(으로|로|을|를|이|가|은|는|과|와)(?![가-힣])')
def fix(m):
    d, p = m.group(1)[-1], m.group(3)
    if p in ('으로', '로'): q = '로' if d in NO | set('178') else '으로'
    else:
        q = p
        for c, v in (('을', '를'), ('이', '가'), ('은', '는'), ('과', '와')):
            if p in (c, v): q = v if d in NO else c
    return m.group(1) + m.group(2) + q
st = collections.Counter()
for proj in ('gt_project_ui_ja', 'gt_project_ui_v2', 'gt_project_v2'):
    bk = os.path.join(B, proj, 'review', '_polish_backup')
    for p in sorted(glob.glob(os.path.join(B, proj, 'gt_output', '*.json'))):
        src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
        dst = json.load(open(p, encoding='utf-8')); ch = False
        for a, b in zip(src, dst):
            m = P.sub(fix, b['message'])
            if proj == 'gt_project_ui_v2' and re.search(r'(?i)\bplanet', a['message']):
                m = re.sub(r'행성(?=[의이을은에])', '별', m)
                m = re.sub(r'(?<![가-힣])행성(?=이|을|은|에)', '별', m)
            if m != b['message']:
                st[proj] += 1
                if DRY: print(repr(b['message'][:70]), '\n ->', repr(m[:70]))
                b['message'] = m; ch = True
        if ch and not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(st), 'DRY' if DRY else '')
