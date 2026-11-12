"""Final pass on the leftover Haiku review items for gt_project_ui_ja (decided 2026-11-12 by majority use
and Rebirth official text). Source-conditioned rules + a few row fixes. Backup in review/_finalfix_backup.
Rejected on purpose: 대미지->데미지, 암흑->어둠, 칼라->컬러, 치유력->회복력, 레어도->레어리티, 슬롯->칸,
解放 variants (context dependent), エネミー variants.
usage: python -I tools/ui_ja_finalfix.py [--dry]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_ui_ja'); DRY = '--dry' in sys.argv
FIX = [('破棄', '파기', '폐기'),                      # tie 19:18, 폐기 reads naturally for data
       ('ウェア', '의상', '웨어'),                    # 웨어 69 vs 의상 5
       ('本戦', '본전투|본전(?!투)', '본선'),          # tournament main round
       ('合成枠', '합성 칸', '합성 슬롯'),             # 슬롯 majority
       ('ショップ', '숍', '상점'),                    # Rebirth 상점 100
       ('決定', '확정', '결정'),                      # Rebirth 결정 31
       ('リトライ', '리트라이', '재시도'),
       ('累計', '누계', '누적'),                      # 누적 25 vs 3
       ('保管庫', '보관고', '보관함'),                # 53 vs 12
       ('ウィッシュリスト', '위시리스트', '위시 리스트'),  # Rebirth
       ('消費', '소모', '소비'),                      # Rebirth 소비 212
       ('サンダー', '썬더', '선더'),                  # Rebirth
       ('エッジ', '에지', '엣지'),
       ('サイレス', '사일레스|사일런스', '사이레스'),   # Rebirth サイレス=사이레스
       ('デブレイ', '데브레이', '디브레이'),          # Rebirth デブレイ=디브레이
       ('デフェイ', '데페이', '디페이'), ('デバリア', '데배리어', '디배리어'), ('デファイ', '데파이', '디파이'),
       ('デブリザ', '데블리자', '디블리자'), ('デサンダ', '데선더', '디선더'),
       ('タンブル', '턴블', '텀블'),
       ('ローズゴールド', '로즈 골드', '로즈골드'),     # 7 vs 1
       ('オーガニクス', '오거나이크스', '오가닉스'),    # Organics
       ('セルリアン', '셀리언', '세룰리안'),          # Cerulean
       ('チョコボの羽根', '초코보의 날개', '초코보의 깃털'),
       ('水鉄砲', '물대포', '물총'),
       ('駆引き上手', '협상에 능한', '수 싸움에 능한'),
       ('売り込んでやろう', '팔아 넘기자', '제보해 보자'),
       ('時>', '時>', '시>'), ('品質', '<品質(★+)以上>', r'<품질\1 이상>')]
FIX = [(re.compile(a), re.compile(b), c) for a, b, c in FIX]
PAIRS = [('을', '를'), ('이', '가'), ('은', '는'), ('과', '와')]
def josa(m, word):
    """make the particle right after `word` (closing quotes/tags may sit between) agree with its last syllable"""
    o = ord(word[-1]) - 0xAC00
    if not 0 <= o < 11172: return m
    b = o % 28  # 0 = no final consonant, 8 = ㄹ
    def fix(x):
        p = x.group(2)
        if p in ('으로', '로'): p = '로' if b in (0, 8) else '으로'
        else:
            for c, v in PAIRS:
                if p in (c, v): p = v if b == 0 else c
        return word + x.group(1) + p
    return re.sub(re.escape(word) + r'((?:[”」』]|</?[a-z_]+(?:=[^>]*)?>)*)(으로|로|을|를|이|가|은|는|과|와)(?![가-힣])', fix, m)
st = collections.Counter(); bk = os.path.join(ROOT, 'review', '_finalfix_backup')
for p in sorted(glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))):
    src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
    dst = json.load(open(p, encoding='utf-8')); ch = False
    for a, b in zip(src, dst):
        m = b['message']
        for e, k, n in FIX:
            if e.search(a['message']) and k.search(m):
                st[n] += len(k.findall(m)); m = josa(k.sub(n, m), n)
        if m != b['message']:
            if DRY: print(repr(b['message'][:60]), '->', repr(m[:60]))
            b['message'] = m; ch = True
    if ch and not DRY:
        os.makedirs(bk, exist_ok=True)
        if not os.path.exists(os.path.join(bk, os.path.basename(p))):
            shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
        json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(st), 'DRY' if DRY else '')
