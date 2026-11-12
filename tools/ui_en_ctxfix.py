"""Context fixes for gt_project_ui_v2 decided from ja_map (ja source): Ultimate Weapon = アルティメット武器
-> 얼티밋 무기, ウェポンパーツ -> 무기 부품, ウェポンメダル -> 무기 메달, 武器 compounds -> 무기, etc.
Particles after the replaced word are re-chosen by final consonant. Backup review/_ctx_backup.
usage: python -I tools/ui_en_ctxfix.py [--dry]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_ui_v2')
DRY = '--dry' in sys.argv
# (English regex in source, Korean regex, replacement)
FIX = [(r'(?i)ultimate weapon', r'얼티밋 웨폰|궁극 무기', '얼티밋 무기'),
       (r'(?i)weapon parts?', r'무기 파츠|웨폰 파츠', '무기 부품'),
       (r'Weapon Medals?', r'무기 훈장|웨폰 메달', '무기 메달'),
       (r'Overboost Weapons', r'오버부스트 웨폰', '오버부스트 무기'),
       (r'Main Weapons?', r'메인 웨폰', '메인 무기'),
       (r'Sub Weapons?', r'서브 웨폰', '서브 무기'),
       (r'Ability Weapons?', r'어빌리티 웨폰', '어빌리티 무기'),
       (r'Lightning Breach', r'라이트닝 브레이크', '라이트닝 브리치'),
       (r'^As Leader$', r'지도자로서', '반장으로서'),
       (r'^Lightning$', r'^라이트닝$', '번개')]
def jong(ch):  # 0 none, 8 = ㄹ, other >0
    o = ord(ch) - 0xAC00
    return (o % 28) if 0 <= o < 11172 else 0
PART = [('으로', '로'), ('이나', '나'), ('이라', '라'), ('이', '가'), ('은', '는'), ('을', '를'), ('과', '와')]
def fixp(new, p):
    j = jong(new[-1])
    for c, v in PART:
        if p in (c, v):
            if c == '으로': return v if j in (0, 8) else c
            return c if j else v
    return p
pr = '(' + '|'.join(sorted({x for t in PART for x in t}, key=len, reverse=True)) + ')?'
FX = [(re.compile(e), re.compile('(' + k + ')' + pr), n) for e, k, n in FIX]
bk = os.path.join(ROOT, 'review', '_ctx_backup'); cnt = collections.Counter(); files = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))):
    src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
    dst = json.load(open(p, encoding='utf-8')); ch = False
    for a, b in zip(src, dst):
        m = b['message']
        for e, k, n in FX:
            if e.search(a['message']):
                m2 = k.sub(lambda mm: n + fixp(n, mm.group(2) or ''), m)
                if m2 != m: cnt[n] += 1; m = m2
        if m != b['message']:
            if DRY and cnt[n] <= 2: print(repr(b['message'][:70]), '->', repr(m[:70]))
            b['message'] = m; ch = True
    if ch:
        files += 1
        if not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))): shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(cnt), 'files', files, 'DRY' if DRY else '')
