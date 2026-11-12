"""Apply accepted Haiku-review fixes to gt_project_v2/gt_output (backup once to review/_apply_backup/).
usage: python -I tools/review_apply.py [--dry]"""
import csv, glob, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_v2')
DRY = '--dry' in sys.argv
rows = list(csv.DictReader(open(os.path.join(ROOT, 'review', 'haiku_all.tsv'), encoding='utf-8'),
                           delimiter='\t', quoting=csv.QUOTE_NONE))

# (tsv row, old, new) — accepted line fixes; \n means a real newline
LINE = [
    (9, '이 나라는 두뇌', '나라는 두뇌'),
    (36, '내 저금은 줄 수 없어?', '내 저금은 못 줘!'),
    (48, '인도해 주는 이들입니다.', '인도해 줍니다.'),
    (50, '슬픈 기억을 하게', '슬픈 일을 겪게'),
    (51, '나에게 들킬 정도니까', '내가 알아낼 정도니까'),
    (52, '죽어!', '죽고 말 거야!'),
    (59, '이 앞이야', '이 안쪽이야'),
    (72, '조금만 있으면', '조금만 더 있었으면'),
    (74, '방해하지 않겠습니다!', '방해는 못 하게 하겠습니다!'),
    (80, '로를 멈춘다', '마황로를 멈춘다'),
    (85, '대회 참가자들이 전부\n불꽃을 망쳐버렸다는군', '대회 참가자들 전부\n누가 불꽃을 망쳐 놨다는군'),
    (120, '요란하게 떨어줄게', '떠들썩하게 놀아 줄게'),
    (122, '더 줘라!', '더 주마!'),
    (148, '죽어야겠다!', '죽어 줘야겠다!'),
    (149, '안질~', '앤질~'),
    (152, '꾀돌이 투성이라네', '능구렁이 투성이라네'),
    (179, '억지로 살아남는 건', '억지로 살려 두는 건'),
    (181, '금방 쓰러뜨린다', '금방 쓰러뜨릴 수 있다'),
    (184, '몬스터를 봉인한', '괴물을 봉인한'),
    (184, '몬스터가 된', '괴물이 된'),
    (185, '제발――', '전부――'),
    (198, '거대한 물결', '물결'),
]

# consonant-final -> vowel-final particle fix
PART = [('을', '를'), ('이', '가'), ('은', '는'), ('과', '와'), ('으로', '로')]
def swap(m, olds, new, vowel_new):
    for o in olds:
        if vowel_new:
            for a, b in PART:
                m = m.replace(o + a, new + b)
        m = m.replace(o, new)
    return m

# (source term, wrong variants, chosen, chosen ends in vowel)
TERM = [
    ('統括', ['통괄'], '총괄', False),                     # Rebirth: 하이데커 총괄
    ('エレノア', ['엘레노어', '엘레노아'], '엘리노어', True),  # Rebirth official
    ('班長', ['분대장', '조장'], '반장', False),
    ('班員', ['조원', '분대원'], '반원', False),
    ('ワゴン', ['카트', '왜건', '웨건'], '수레', True),
    ('歳獣', ['세수'], '새해 짐승', False),
    ('バカリンゴ', ['바카링고', '바보 사과'], '바보사과', False),
    ('スラクト', ['슬라크트'], '슬락트', False),
    ('ビーチフェス', ['비치 페스티벌'], '비치 페스', True),
    ('アースナル', ['어스널'], '아스널', False),
    ('虎の巻', ['비전서'], '비법서', False),
    ('元ソルジャー', ['전 솔저'], '전직 솔저', False),
    ('治安維持部門', ['치안 유지 부서', '치안유지부문'], '치안 유지 부문', False),
]

files = {}
def load(f):
    if f not in files:
        files[f] = (json.load(open(os.path.join(ROOT, 'gt_input', f), encoding='utf-8')),
                    json.load(open(os.path.join(ROOT, 'gt_output', f), encoding='utf-8')), [False])
    return files[f]

log = []
for r, old, new in LINE:
    x = rows[r]; f, i = x['file'], int(x['idx'])
    src, dst, ch = load(f)
    m = dst[i]['message']
    if old not in m:
        print('MISS', r, f, i, repr(old)); continue
    dst[i]['message'] = m.replace(old, new, 1); ch[0] = True
    log.append(('line', f, i, m, dst[i]['message']))

for p in glob.glob(os.path.join(ROOT, 'gt_input', '*.json')):
    f = os.path.basename(p); src, dst, ch = load(f)
    for i, (a, b) in enumerate(zip(src, dst)):
        m0 = m = b.get('message', '')
        for t, olds, new, v in TERM:
            if t in a.get('message', ''):
                m = swap(m, olds, new, v)
        m = re.sub(r'“‘([^’”]*)’', r'“\1”', m)          # “‘X’ -> “X”
        if m != m0:
            b['message'] = m; ch[0] = True
            log.append(('auto', f, i, m0, m))

n = 0
bk = os.path.join(ROOT, 'review', '_apply_backup')
for f, (src, dst, ch) in files.items():
    if not ch[0]: continue
    n += 1
    if DRY: continue
    os.makedirs(bk, exist_ok=True)
    out = os.path.join(ROOT, 'gt_output', f)
    if not os.path.exists(os.path.join(bk, f)):
        shutil.copy2(out, os.path.join(bk, f))
    json.dump(dst, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

with open(os.path.join(ROOT, 'review', '_apply_log.tsv'), 'w', encoding='utf-8') as fo:
    for k, f, i, a, b in log:
        fo.write('%s\t%s\t%d\t%s\t%s\n' % (k, f, i, a.replace('\n', '⏎'), b.replace('\n', '⏎')))
print('changed lines', len(log), '(line %d, auto %d)' % (sum(l[0] == 'line' for l in log), sum(l[0] == 'auto' for l in log)),
      'files', n, 'DRY' if DRY else '')
