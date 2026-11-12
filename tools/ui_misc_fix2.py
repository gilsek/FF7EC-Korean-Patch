"""Small unify fixes found in ja/en mismatch review.
- 크라이테리언/크리테리언 -> 크라이테리온 (majority form)
- 맷를 -> 맷을 (josa after final consonant)
usage: python -I tools/ui_misc_fix2.py"""
import glob, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RULES = [(re.compile('크라이테리언|크리테리언'), '크라이테리온'),
         (re.compile(r'맷를(?![가-힣])'), '맷을')]
n = 0
for proj in ('gt_project_ui_v2', 'gt_project_ui_ja'):
    for p in glob.glob(os.path.join(B, proj, 'gt_output', '*.json')):
        O = json.load(open(p, encoding='utf-8')); ch = False
        for e in O:
            s = e['message']
            for rx, rep in RULES:
                s = rx.sub(rep, s)
            if s != e['message']:
                print(proj, os.path.basename(p), e['message'][:40], '->', s[:40])
                e['message'] = s; ch = True; n += 1
        if ch:
            json.dump(O, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n)
