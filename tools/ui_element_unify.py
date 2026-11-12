"""Unify element names to FF7 Rebirth official style (염/빙/뇌/풍/토/수/암/광 + 속성) in both UI projects,
conditioned on the element appearing in the source row. Also 데미지 -> 대미지 (Rebirth: 대미지 458, 데미지 0),
and status 暗闇/Darkness -> 암흑 (FFT official). Backup in <proj>/review/_element_backup.
usage: python -I tools/ui_element_unify.py [--dry] [-v]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
DRY = '--dry' in sys.argv; V = '-v' in sys.argv
# target, ja source regex, en source regex, Korean variants
EL = [('염', '炎', r'(?i)\b(fire|flame)', '화염|불|염|화'),
      ('빙', '[氷冷]', r'(?i)\bice', '냉기|얼음|빙|냉'),
      ('뇌', '雷', r'(?i)\b(lightning|ltng)', '번개|뇌|전기'),
      ('풍', '風', r'(?i)\bwind', '바람|풍'),
      ('토', '土', r'(?i)\bearth', '대지|땅|토양|흙|토'),
      ('수', '水', r'(?i)\bwater', '물|수'),
      ('암', '闇', r'(?i)\bdark\b', '어둠|암흑|암'),
      ('광', '光', r'(?i)\b(light|holy)\b', '빛|광')]
NEXT = r'(?=(내성|저항|피해|대미지|데미지|약점|공격|마법|버프|디버프|흡수|무효|반감|강화|부여|위력|威力|UP|업|다운|DOWN|증가|감소|상승|하강|저하)(?![가-힣]*의 ))'
RULES = []
for t, ja, en, v in EL:
    jre = re.compile(ja + r'(属性|耐性|弱点|・|ダメージ|威力|魔法|攻撃)|[炎氷冷雷風土水闇光]・' + ja)
    ere = re.compile(en)  # source only needs the element word; the Korean side requires an element context
    k1 = re.compile(r'(?<![가-힣])(' + v + r') ?속성')                 # X 속성 -> T속성
    k2 = re.compile(r'(?<![가-힣])(' + v + r') ' + NEXT)               # X 내성 -> T속성 내성
    k3 = re.compile(r'(?<![가-힣])(' + v + r')(?=[・ㆍ,/] ?(' + '|'.join(e[3] for e in EL) + '))')  # list item
    k4 = re.compile(r'(?<=[・ㆍ,/] )(' + v + r')(?= ?속성)|(?<=[・ㆍ,/])(' + v + r')(?= ?속성)')
    RULES.append((t, jre, ere, k1, k2, k3, k4))
DARK_JA = re.compile('暗闇'); DARK_EN = re.compile(r'\bDarkness\b')
DARK_KO = re.compile(r'(?<![가-힣])어둠(?![가-힣])')  # standalone token only (status name)
st = collections.Counter(); samples = collections.defaultdict(list)
for proj, lang in (('gt_project_ui_ja', 'ja'), ('gt_project_ui_v2', 'en')):
    root = os.path.join(HERE, '..', proj); bk = os.path.join(root, 'review', '_element_backup')
    for p in sorted(glob.glob(os.path.join(root, 'gt_output', '*.json'))):
        src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
        dst = json.load(open(p, encoding='utf-8')); ch = False
        for a, b in zip(src, dst):
            s, m0 = a['message'], b['message']; m = m0
            for t, jre, ere, k1, k2, k3, k4 in RULES:
                if (jre if lang == 'ja' else ere).search(s):
                    m = k1.sub(t + '속성', m)
                    m = k2.sub(t + '속성 ', m)
                    m = k3.sub(t, m)
                    m = k4.sub(t, m)
            m = re.sub(r'([염빙뇌풍토수암광])속성속성', r'\1속성', m)
            if (DARK_JA if lang == 'ja' else DARK_EN).search(s) and not re.search('闇属性|\\bDark\\b', s):
                m = DARK_KO.sub('암흑', m)
            m = m.replace('데미지', '대미지')
            if m != m0:
                st[proj] += 1; b['message'] = m; ch = True
                if len(samples[proj]) < 400: samples[proj].append((s, m0, m))
        if ch and not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
out = os.path.join(HERE, '..', 'work', 'element_unify_diff.tsv')
with open(out, 'w', encoding='utf-8') as f:
    for proj, L in samples.items():
        for s, a, b in L: f.write('\t'.join([proj] + [x.replace('\n', '⏎') for x in (s, a, b)]) + '\n')
print(dict(st), 'diff ->', out, 'DRY' if DRY else '')
