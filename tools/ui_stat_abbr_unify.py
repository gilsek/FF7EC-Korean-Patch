"""en-source UI polish (match ja-source wording):
- PATK/MATK/PDEF/MDEF -> 물공/마공/물방/마방 (+ josa after final consonant ㅇ)
- 'FIRST 솔저' -> 'FIRST SOLDIER' (game title stays English, as in ja-source UI)
- '내성 UP/DOWN', '획득률 UP' -> 상승/하락
usage: python -I tools/ui_stat_abbr_unify.py"""
import glob, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ABBR = {'PATK': '물공', 'MATK': '마공', 'PDEF': '물방', 'MDEF': '마방'}
# particle after a word with final consonant
JOSA = {'를': '을', '을': '을', '가': '이', '이': '이', '는': '은', '은': '은', '와': '과', '과': '과', '로': '으로', '으로': '으로'}
RX = re.compile(r'(?<![A-Za-z])(PATK|MATK|PDEF|MDEF)(?![A-Za-z])(</color>)?(으로|를|을|가|이|는|은|와|과|로)?(?![가-힣])')
def sub(m):
    return ABBR[m.group(1)] + (m.group(2) or '') + (JOSA[m.group(3)] if m.group(3) else '')
OTHER = [(re.compile(r'FIRST 솔저'), 'FIRST SOLDIER'),
         (re.compile(r'(내성|획득률) UP\b'), r'\1 상승'),
         (re.compile(r'(내성) DOWN\b'), r'\1 하락')]
n = 0
for p in glob.glob(os.path.join(B, 'gt_project_ui_v2', 'gt_output', '*.json')):
    O = json.load(open(p, encoding='utf-8')); ch = False
    for e in O:
        s = RX.sub(sub, e['message'])
        for rx, rep in OTHER:
            s = rx.sub(rep, s)
        if s != e['message']:
            e['message'] = s; ch = True; n += 1
    if ch:
        json.dump(O, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n)
