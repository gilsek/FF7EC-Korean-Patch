"""ja-source mission text: literal '~にする' -> natural Korean.
레벨/레어리티를 X로 한다 -> X까지 올린다, 탐색률을 X로 한다 -> X 달성, ON으로 한다 -> ON으로 설정한다.
usage: python -I tools/ui_ja_mission_polish.py"""
import glob, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RULES = [
    (re.compile(r'(레벨|레어리티|레어도)([을를])(.+? 이상)으로 한다'), r'\1\2\3으로 올린다'),
    (re.compile(r'(레벨|레어리티|레어도)([을를])(.+?)(?:으로|로) 한다'), r'\1\2\3까지 올린다'),
    (re.compile(r'(Lv\.\s?\{?\d+\}?)(?:으로|로) 한다'), r'\1까지 올린다'),
    (re.compile(r'(탐색률)을 (\S+?)(?:으로|로) 한다'), r'\1 \2 달성'),
    (re.compile(r'(ON|OFF)으로 한다'), r'\1으로 설정한다'),
]
n = 0
for p in glob.glob(os.path.join(B, 'gt_project_ui_ja', 'gt_output', '*.json')):
    O = json.load(open(p, encoding='utf-8')); ch = False
    for e in O:
        s = e['message']
        for rx, rep in RULES:
            s = rx.sub(rep, s)
        if s != e['message']:
            print(os.path.basename(p), '|', e['message'][:50].replace('\n', ' '), '->', s[:50].replace('\n', ' '))
            e['message'] = s; ch = True; n += 1
        elif re.search(r'(?:으로|로) 한다', s):
            print('LEFT', os.path.basename(p), '|', s[:70].replace('\n', ' '))
    if ch:
        json.dump(O, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n)
