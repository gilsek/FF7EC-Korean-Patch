"""Restore <...> tags in gt_output to the source tags when the model rewrote them
(same tag count -> replace in order; otherwise report). Backup in review/_tag_backup.
usage: python -I tools/tag_restore.py PROJECT_DIR [--dry]"""
import glob, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = sys.argv[1]; DRY = '--dry' in sys.argv
TAG = re.compile(r'<[^<>\n]+>')
bk = os.path.join(ROOT, 'review', '_tag_backup')
fixed, left = 0, []
for p in sorted(glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))):
    src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
    dst = json.load(open(p, encoding='utf-8')); ch = False
    for i, (a, b) in enumerate(zip(src, dst)):
        st, dt = TAG.findall(a['message']), TAG.findall(b['message'])
        if st == dt:
            continue
        if len(st) == len(dt):
            it = iter(st)
            b['message'] = TAG.sub(lambda m: next(it), b['message']); ch = True; fixed += 1
        else:
            left.append((os.path.basename(p), i, a['message'][:70], b['message'][:70]))
    if ch and not DRY:
        os.makedirs(bk, exist_ok=True)
        if not os.path.exists(os.path.join(bk, os.path.basename(p))):
            shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
        json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('fixed', fixed, 'left', len(left), 'DRY' if DRY else '')
for x in left:
    print('LEFT', x[0], x[1], repr(x[2]), '|', repr(x[3]))
