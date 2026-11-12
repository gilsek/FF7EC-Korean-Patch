"""Rebirth-style unify across UI (en/ja) and story:
- 마황로 N -> N번 마황로 (Rebirth: N번 마황로). UI 'Mako Reactor 1' (마황로 1호기 once) also -> 1번 마황로.
  Keep story 魔晄炉１号機 (Jenova project log, Nibelheim's first reactor) as 마황로 1호기 - not Midgar's 壱番魔晄炉.
- 월페이퍼 -> 배경화면 (majority)
- 시질 -> 시길 (Rebirth)
- 'XX 월페이퍼' josa unaffected (both end without final consonant? 배경화면 ends with ㄴ!) -> fix 를/가/는/와/로 after it.
usage: python -I tools/term_unify3.py"""
import glob, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
JOSA = {'를': '을', '가': '이', '는': '은', '와': '과', '로': '으로', '라': '이라', '예요': '이에요', '야': '이야'}
RULES = [
    (re.compile(r'(?<![가-힣\d])마황로 ([1-8])(?![\d개회번호])'), r'\1번 마황로'),
    (re.compile(r'월페이퍼(를|가|는|와|로|라|예요|야)?(?![가-힣])'), lambda m: '배경화면' + (JOSA[m.group(1)] if m.group(1) else '')),
    (re.compile(r'월페이퍼'), '배경화면'),
    (re.compile(r'시질'), '시길'),
]
n = 0
for proj in ('gt_project_ui_v2', 'gt_project_ui_ja', 'gt_project_v2'):
    for p in glob.glob(os.path.join(B, proj, 'gt_output', '*.json')):
        O = json.load(open(p, encoding='utf-8')); ch = False
        for e in O:
            s = e['message']
            for rx, rep in RULES:
                s = rx.sub(rep, s)
            if s != e['message']:
                if n < 12: print(proj[-5:], e['message'][:50].replace('\n', '/'), '->', s[:50].replace('\n', '/'))
                e['message'] = s; ch = True; n += 1
        if ch:
            json.dump(O, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n)
