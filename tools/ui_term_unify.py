"""Source-conditioned spelling unification across UI ja/en and story projects.
カラー/Collar = Red XIII weapon (Rebirth: ミスリルカラー=미스릴 칼라) -> 칼라 (not ラッキーカラー);
タンブリン/Tamblin -> 탐블린; サブマスター -> 서브 마스터; アナザー -> 어나더.
Backup in <proj>/review/_termunify_backup.  usage: python -I tools/ui_term_unify.py [--dry]"""
import glob, json, os, re, shutil, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); DRY = '--dry' in sys.argv
# (source regex, Korean regex, replacement)
FIX = [(r'(?<!ラッキー)カラー|\bCollar', '컬러', '칼라'),
       (r'タンブリン|Tamblin', '탬블린|탐브린|탄브린|탬버린', '탐블린'),
       (r'サブマスター|Sub-?[Mm]aster', '부마스터|서브마스터', '서브 마스터'),
       (r'アナザー|\bAnother\b', '아나더', '어나더'),
       (r'古代種|\bAncients?\b', '고대종족', '고대종'),          # Rebirth 古代種の神殿=고대종의 신전
       (r'Ancient Festival Garb', '고대 축제의 의상|고대인의 축제 의상', '고대종의 축제 의상'),
       (r'Reunion among the Flowers', '꽃들 속의 재회', '꽃들 사이의 재회')]
FIX = [(re.compile(a), re.compile(b), c) for a, b, c in FIX]
st = collections.Counter()
for proj in ('gt_project_ui_ja', 'gt_project_ui_v2', 'gt_project_v2'):
    root = os.path.join(HERE, '..', proj); bk = os.path.join(root, 'review', '_termunify_backup')
    for p in sorted(glob.glob(os.path.join(root, 'gt_output', '*.json'))):
        src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
        dst = json.load(open(p, encoding='utf-8')); ch = False
        for a, b in zip(src, dst):
            m = b['message']
            for e, k, n in FIX:
                if e.search(a['message']) and k.search(m):
                    st[proj[3:] + ':' + n] += len(k.findall(m)); m = k.sub(n, m)
            if m != b['message']: b['message'] = m; ch = True
        if ch and not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(dict(st), 'DRY' if DRY else '')
