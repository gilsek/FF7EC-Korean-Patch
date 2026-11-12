"""Name/term normalization for gt_project_ui_v2 (English source), conditioned on the English name
appearing in the source row. Built from work/en_name_summary.txt + Haiku review. Backup in
review/_namefix_backup.
usage: python -I tools/en_name_fix.py [--dry]"""
import glob, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_ui_v2')
DRY = '--dry' in sys.argv
# (English regex in source, Korean regex in translation, replacement)
FIX = [
    (r'Angeal', '안질', '앤질'),
    (r'Lucia', '루시아', '루티아'),
    (r'Matt', '매트', '맷'),
    (r'Ex-SOLDIER', r'(?<![가-힣])전 (솔저|SOLDIER)', '전직 솔저'),
    (r'SOLDIER', 'SOLDIER', '솔저'),
    (r'Limit Breaks?', '한계 돌파', '리미트 브레이크'),
    (r'Cactuars?', '캑터스?', '사보텐더'),
    (r'Reno', '리노', '레노'),
    (r'Behemoth', '비히모스', '베히모스'),
    (r'Cloud', '크라우드', '클라우드'),
    (r'Barret', '바렛|배럿', '바레트'),
    (r'Nibelheim', '니블하임', '니블헤임'),
    (r'Kunsel', '쿤셀', '칸셀'),
    (r'Tseng', '츠엥|츠옹', '청'),
    (r'Marlene', '마를린', '마린'),
    (r'Dumbapples?', '덤애플', '바보사과'),
    (r'Zack', '잭(?!스)', '잭스'),
    (r'Heidegger', '하이데거', '하이데커'),
    (r'Palmer', '파머', '팔머'),
    (r'Elmyra', '엘미라', '엘미나'),
    (r'Refu', '레푸', '레퓨'),
    (r'Ifalna', '이팔나', '이파르나'),
    (r'Hojo', '호죠', '호조'),
    (r'Biggs', '비그스', '빅스'),
    (r'Zangan', '장간', '잔간'),
    (r'Cait Sith', '케이트 시스|캐트 시스', '캐트시'),
    (r'(Vincent|Grimoire) Valentine', '(빈센트|그리모어) 발렌타인', r'\1 밸런타인'),  # not Valentine's Day
    (r'Lucrecia', '루크레시아', '루크레치아'),
    (r'Junon', '쥬논', '주논'),
    (r'Dachao', '다차오|다쵸', '다챠오'),
    (r'Modeoheim', '모데오하임', '모데오헤임'),
    (r'Leviathan', '리바이어선', '리바이어던'),
    (r'[Mm]ako [Rr]eactors?', '마황 리액터', '마황로'),
    (r'Corel Prison', '코렐 감옥', '코렐 프리즌'),
    (r'President Shinra', '신라 사장', '프레지던트 신라'),
]
FIX = [(re.compile(r'\b' + e + r'\b'), re.compile(k), n) for e, k, n in FIX]
bk = os.path.join(ROOT, 'review', '_namefix_backup')
cnt, files, rows = {}, 0, 0
for p in sorted(glob.glob(os.path.join(ROOT, 'gt_output', '*.json'))):
    src = json.load(open(p.replace('gt_output', 'gt_input'), encoding='utf-8'))
    dst = json.load(open(p, encoding='utf-8')); ch = False
    for a, b in zip(src, dst):
        m = b['message']
        for e, k, n in FIX:
            if e.search(a['message']) and k.search(m):
                cnt[n] = cnt.get(n, 0) + len(k.findall(m)); m = k.sub(n, m)
        if m != b['message']:
            rows += 1
            if DRY and rows % 60 == 1:
                print(repr(b['message'][:60]), '->', repr(m[:60]))
            b['message'] = m; ch = True
    if ch:
        files += 1
        if not DRY:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))):
                shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            json.dump(dst, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(cnt, 'rows', rows, 'files', files, 'DRY' if DRY else '')
