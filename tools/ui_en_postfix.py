"""Term normalization for UI rows translated from English (gt_project_ui_v2): the ja-keyed glossary
did not hit English source, so official terms drifted. Backup in review/_postfix_backup.
usage: python -I tools/ui_en_postfix.py [PROJECT_DIR] [--dry]"""
import glob, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_ui_v2')
DRY = '--dry' in sys.argv
TERMS = [(r'(?<!휴)마코(?!토)', '마황'), ('터크스', '턱스'), ('크리스탈', '크리스털'), ('아발란체', '아발란치'), ('미드갈', '미드가르')]
GIL_EN = re.compile(r'\bGil\b')
GIL_KO = re.compile(r'길(?!드)')
bk = os.path.join(ROOT, 'review', '_postfix_backup')
cnt, files = {}, 0
for p in sorted(glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))):
    src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
    dst = json.load(open(p, encoding='utf-8')); ch = False
    for a, b in zip(src, dst):
        m = b['message']
        for o, n in TERMS:
            k = len(re.findall(o, m))
            if k:
                cnt[o] = cnt.get(o, 0) + k; m = re.sub(o, n, m)
        if GIL_EN.search(a['message']) and GIL_KO.search(m):
            cnt['길→GIL'] = cnt.get('길→GIL', 0) + 1; m = GIL_KO.sub('GIL', m)
        if m != b['message']:
            b['message'] = m; ch = True
    if ch:
        files += 1
        if not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(cnt, 'files', files, 'DRY' if DRY else '')
