"""Source-conditioned term fixes for gt_project_ui_ja (from Haiku review): replace a Korean variant
only in rows whose ja source contains the key. Backup in review/_termfix_backup.
usage: python -I tools/ui_ja_termfix.py [--dry]"""
import glob, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_ui_ja')
DRY = '--dry' in sys.argv
# (ja key in source, regex on translation, replacement)
FIX = [('村雨', '무라마사', '무라사메'),
       ('金剛坊', '콩고보', '금강방'),
       ('元ソルジャー', r'(?<![가-힣])전 솔저', '전직 솔저'),
       ('戦歴', '전력', '전적')]
bk = os.path.join(ROOT, 'review', '_termfix_backup')
cnt, files = {}, 0
for p in sorted(glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))):
    src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
    dst = json.load(open(p, encoding='utf-8')); ch = False
    for a, b in zip(src, dst):
        m = b['message']
        for k, o, n in FIX:
            if k in a['message'] and re.search(o, m):
                cnt[k] = cnt.get(k, 0) + 1; m = re.sub(o, n, m)
        if m != b['message']:
            if DRY:
                print(repr(b['message'][:60]), '->', repr(m[:60]))
            b['message'] = m; ch = True
    if ch:
        files += 1
        if not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(cnt, 'files', files, 'DRY' if DRY else '')
