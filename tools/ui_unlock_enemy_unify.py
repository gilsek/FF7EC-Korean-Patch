"""Context-checked unification of 解放/unlock and エネミー/enemy in the UI (ja + en projects), 2026-11-12.
- feature/content/slot unlock (解放, unlock) -> 개방 (Rebirth: 개방 조건, 개방되었습니다)
- level-cap release (上限解放, LV Uncap / level cap / level limit) -> 상한 해방
- マス (grid square) / en Node -> 칸
- generic エネミー/enemy -> 적 (Rebirth 179:26); terms kept: 심볼 에너미, 에너미 심볼, 에너미 런처
All rows checked by hand beforehand (work/opus_review/kaiho_enemy.tsv). Particles are re-fixed after each swap.
Backup in <proj>/review/_unlock_backup.  usage: python -I tools/ui_unlock_enemy_unify.py [--dry]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); DRY = '--dry' in sys.argv
PAIRS = [('을', '를'), ('이', '가'), ('은', '는'), ('과', '와')]
def josa(m, word):
    o = ord(word[-1]) - 0xAC00; b = o % 28
    def fix(x):
        p = x.group(2)
        if p in ('으로', '로'): p = '로' if b in (0, 8) else '으로'
        else:
            for c, v in PAIRS:
                if p in (c, v): p = v if b == 0 else c
        return word + x.group(1) + p
    return re.sub(re.escape(word) + r'((?:[”」』"]|</?[a-z_]+(?:=[^>]*)?>)*)(으로|로|을|를|이|가|은|는|과|와)(?![가-힣])', fix, m)
def sub(m, pat, new, st, key):
    n = len(re.findall(pat, m))
    if not n: return m
    st[key] += n
    return josa(re.sub(pat, new, m), new.split()[-1] if ' ' in new else new)

def ja_rule(s, m, st):
    if '上限解放' in s:
        m = sub(m, r'상한 (?:해제|개방)', '상한 해방', st, 'ja:상한 해방')
        m = sub(m, r'상한을 해제', '상한을 해방', st, 'ja:상한 해방')
    if re.search(r'解放', s):
        pat = r'(?<!상한 )(?<!상한을 )해방|해금' + ('' if '解除' in s else r'|(?<!상한 )(?<!상한을 )해제')
        m = sub(m, pat, '개방', st, 'ja:개방')
    if re.search(r'マス(?![タクカコ])', s):
        m = sub(m, r'마스(?![터크카코쿠])', '칸', st, 'ja:칸')
    if 'エネミー' in s:
        m = sub(m, r'(?<!심볼 )에너미(?! 런처| 심볼)', '적', st, 'ja:적')
        m = sub(m, r'(?<=보스 )몬스터|(?<=기타 )몬스터', '적', st, 'ja:적')
    m = re.sub(r'(상한이 \{\d\}에서 )개방', r'\1해방', m)   # レベル上限が{0}で解放 = level-cap release
    return m

def en_rule(s, m, st):
    if re.search(r'(?i)uncap|level (?:cap|limit)', s):
        m = sub(m, r'상한 (?:해제|개방)', '상한 해방', st, 'en:상한 해방')
        m = sub(m, r'상한을 해제', '상한을 해방', st, 'en:상한 해방')
    if re.search(r'(?i)\bunlock|\blocked\b|now available|become available', s):
        rem = re.search(r'(?i)remov|lift|cancel|dispel|releas|clear|uncap', s)
        pat = r'(?<!상한 )(?<!상한을 )해방|해금' + ('' if rem else r'|(?<!상한 )(?<!상한을 )해제')
        m = sub(m, pat, '개방', st, 'en:개방')
    if re.search(r'(?i)\bnodes?\b', s):          # same grid as ja マス -> 칸
        m = sub(m, r'노드', '칸', st, 'en:칸')
    if re.search(r'(?i)enemy abilit|\bE\. abilit', s):       # = てきのわざ, Rebirth 적의 기술
        m = sub(m, r'(?:적|에너미) 어빌리티', '적의 기술', st, 'en:적의 기술')
    if re.search(r'\bR\. Enemy', s): m = sub(m, r'R\. 에너미', '레어 적', st, 'en:적')
    if re.search(r'(?i)symbol enem', s):
        m = sub(m, r'심볼 적', '심볼 에너미', st, 'en:심볼 에너미')
    if re.search(r'(?i)rare enem', s): m = sub(m, r'레어 에너미', '레어 적', st, 'en:적')
    if re.search(r'(?i)boss enem', s): m = sub(m, r'보스 (?:몬스터|에너미)', '보스 적', st, 'en:적')
    return m

st = collections.Counter()
for proj, rule in (('gt_project_ui_ja', ja_rule), ('gt_project_ui_v2', en_rule)):
    bk = os.path.join(B, proj, 'review', '_unlock_backup')
    for p in sorted(glob.glob(os.path.join(B, proj, 'gt_output', '*.json'))):
        src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
        dst = json.load(open(p, encoding='utf-8')); ch = False
        for a, b in zip(src, dst):
            m = rule(a['message'], b['message'], st)
            if m != b['message']:
                if DRY: print(proj[11:], repr(b['message'][:60]), '\n   ->', repr(m[:60]))
                b['message'] = m; ch = True
        if ch and not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(st), 'DRY' if DRY else '')
