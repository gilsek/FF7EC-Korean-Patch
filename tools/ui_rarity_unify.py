"""Rarity -> 희귀도 (FF7 Rebirth official Korean). 레어도/레어리티 mixed before.
All three end in a vowel, so following particles stay valid.
Also restores a missing trailing blank line in ui__Steam idx111.
usage: python -I tools/ui_rarity_unify.py"""
import glob, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RX = re.compile('레어리티|레어도')
n = 0
for proj in ('gt_project_ui_v2', 'gt_project_ui_ja'):
    for p in glob.glob(os.path.join(B, proj, 'gt_output', '*.json')):
        O = json.load(open(p, encoding='utf-8')); ch = False
        I = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
        for a, e in zip(I, O):
            s = RX.sub('희귀도', e['message'])
            if s != e['message']:
                e['message'] = s; ch = True; n += 1
        if os.path.basename(p) == 'ui__Steam.json':
            src, k = I[111]['message'], O[111]['message']
            want = len(src) - len(src.rstrip('\n')); have = len(k) - len(k.rstrip('\n'))
            if want > have:
                O[111]['message'] = k + '\n' * (want - have); ch = True; print('steam111 +', want - have)
        if ch:
            json.dump(O, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n)
