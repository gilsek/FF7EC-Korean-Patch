"""Apply accepted Haiku review fixes to gt_project_movie/gt_output (backup in review/_apply_backup).
usage: python -I tools/movie_review_apply.py"""
import glob, json, os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_movie')
P = 'moviesubtitles__'
LINE = [
    (P + 'battle_wave__battle_wave_end2_004_01.json', 23, '이어받은 범인', '이어받은 평범한 인간'),
    (P + 'story__eg__story_eg_031.json', 1, '따, 딴 사람 얘기를', '따, 딱히 네 얘기를'),
    (P + 'story__eg__story_eg_041.json', 7, '아직 멀었어……', '무르네……'),
    (P + 'story__eg__story_eg_042.json', 23, '들으키로', '듣기로'),
    (P + 'story__eg__story_eg_043.json', 15, '클라우드 일\n감사했습니다!', '클라우드를 챙겨 주셔서\n감사했습니다!'),
    (P + 'story__eg__story_eg_051.json', 3, '나도 진심을 내야지', '나도 진지하게 나서야지'),
    (P + 'story__eg__story_eg_051.json', 5, '선배도 초보시니까요', '선배가 초보시니까요'),
]
GLOBAL = [('솔저 클래스 1ST', '솔저 1st'), ('미도가루시', '미드가르시'), ('팀 성투라', '팀 세이토라'),
          ('칠고', '7고'), ('(아바란치)', '(아발란치)')]
bk = os.path.join(ROOT, 'review', '_apply_backup'); os.makedirs(bk, exist_ok=True)
files, n, miss = {}, 0, 0
def load(f):
    if f not in files:
        files[f] = json.load(open(os.path.join(ROOT, 'gt_output', f), encoding='utf-8'))
    return files[f]
for f, i, a, b in LINE:
    d = load(f)
    if a not in d[i]['message']:
        print('MISS', f, i, repr(a)); miss += 1; continue
    d[i]['message'] = d[i]['message'].replace(a, b, 1); n += 1
for p in glob.glob(os.path.join(ROOT, 'gt_output', '*.json')):
    d = load(os.path.basename(p))
    for x in d:
        m = x['message']
        for a, b in GLOBAL:
            m = m.replace(a, b)
        if m != x['message']:
            x['message'] = m; n += 1
changed = 0
for f, d in files.items():
    out = os.path.join(ROOT, 'gt_output', f)
    if json.load(open(out, encoding='utf-8')) == d:
        continue
    if not os.path.exists(os.path.join(bk, f)):
        shutil.copy2(out, os.path.join(bk, f))
    json.dump(d, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); changed += 1
print('changes', n, 'files', changed, 'miss', miss)
