"""Apply accepted tone/unnatural fixes from haiku_all.tsv (2nd pass). Same backup dir as review_apply.py.
usage: python -I tools/review_apply_tone.py [--dry]"""
import csv, glob, json, os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gt_project_v2')
DRY = '--dry' in sys.argv
rows = list(csv.DictReader(open(os.path.join(ROOT, 'review', 'haiku_all.tsv'), encoding='utf-8'),
                           delimiter='\t', quoting=csv.QUOTE_NONE))
LINE = [
    (0, '데이트 1회,였지?', '데이트 1회였지?'),
    (1, '방해하러 왔어, 이 말이야.', '방해 좀 하겠다고, 이 말이야.'),
    (8, '그런 마음을 들게 해서', '그런 마음을 갖게 해서'),
    (13, '츸쓸한', '싸늘한'),
    (18, '나쁜 쪽으로!', '악운 하나는!'),
    (19, '운이 나쁜 쪽으로 트였네', '악운이 붙은 모양이네'),
    (20, '불룩해지지 마', '퍼지지 마'),
    (23, '친구나 동료가 될 수는', '동지나 친구가 될 수는'),
    (25, '여러 가지 있겠죠?\n잠시 내버려 두는 게 좋겠어요', '여러 가지 있겠지?\n잠시 내버려 두는 게 좋겠어'),
    (26, '눈치채셨다면\n이제 괜찮으시죠?', '눈치챘으면\n이제 괜찮지?'),
    (29, '하고 있단다', '하고 있어'),
    (30, '이봐!', '정말!'),
    (32, '이게 무슨 수야', '무슨 수가 이렇게'),
    (34, '이~이!!', '정말~!!'),
    (35, '짜디짠', '쩨쩨한'),
    (45, '그녀에 대해서는 걱정하지 마시게.', '그녀 걱정은 하지 마라.'),
    (45, '포함되어 있네.', '포함되어 있다.'),
    (46, '소중한 아이입니다.', '소중한 아이야.'),
    (46, '이어받았으니까요.', '이어받았으니까.'),
    (47, '피입니다.', '피야.'),
    (49, '맡아줄 수 없겠나?', '맡아 줄 수 없겠냐?'),
    (53, '응!?', '어!?'),
    (54, '응!?', '어!?'),
    (55, '해볼 텐가!?', '한판 붙자는 거냐!?'),
    (56, '괜찮아?', '괜찮으세요?'),
    (62, '들니까', '드니까'),
    (63, '도망쳐!!', '도망치세요!!'),
    (67, '드물니까', '드무니까'),
    (69, '꽤나 돌아왔어', '꽤 돌아서 왔네'),
    (73, '축복한 것이었다', '축복했다'),
    (81, '상시 여름의', '늘 여름인'),
    (92, '조심하게!', '조심해!'),
    (93, '자네도 함께 와 주게.', '너도 함께 와 줘.'),
    (97, '당신 컬렉션은', '네 컬렉션은'),
    (98, '도둑과 절', '도둑과 저를'),
    (106, '내가 뭐라는 거야!', '내가 뭔 줄 알고!'),
    (107, '처음 봤다냥', '처음 봤심다'),
    (108, '저입니다.', '나다.'),
    (109, '미안하군요, 아버지.', '미안하군, 아버지.'),
    (111, '네들', '너희들'),
    (112, '흡……', '훗……'),
    (114, '부름받았던 거야.', '부름받았던 겁니다.'),
    (115, '나, 왔어.\n흑 마테리아, 가져왔어.', '저, 왔습니다.\n흑 마테리아, 가져왔습니다.'),
    (116, '보여 줘.\n어디에 있는 거야?', '보여 주세요.\n어디에 계신 겁니까?'),
    (117, '만났네――', '만났네요――'),
    (121, '다른 곳에 있는 거야.', '다른 곳에 있는 걸세.'),
    (124, '유피 님이', '유피 짱이'),
    (125, '자, 그만둬!', '잠깐, 그만둬!'),
    (155, '한낱 한순간', '그저 한순간'),
    (173, '과거의 쌓임이 지금의 너인 거니까.', '과거가 쌓여서 지금의 네가 된 거니까.'),
    (174, '이상할 정도라고', '신기할 정도라고'),
    (175, '이길 수 있다……\n라도 말할 셈인가?', '이길 수 있다고……\n말할 셈인가?'),
    (176, '필요 없다.\n조사에 전념해.', '필요 없습니다.\n조사에 전념해 주십시오.'),
    (177, '유피쨩', '유피 짱'),
    (182, '여기까지 왔어요', '여기까지 왔다'),
    (183, '당신을 지키겠다고', '너를 지키겠다고'),
    (187, '왜냐!', '왜지!'),
    (189, '빈센트 양은', '빈센트 씨는'),
    (191, '기묘한 우연이네요', '이런 우연이 다 있네요'),
    (192, '모르겠군요', '모르겠습니다'),
]
TERM = [('勇者', '용자', '용사'), ('ユフィちゃん', '유피쨩', '유피 짱'), ('ヴィンセントはん', '빈센트 양', '빈센트 씨')]

files = {}
def load(f):
    if f not in files:
        files[f] = (json.load(open(os.path.join(ROOT, 'gt_input', f), encoding='utf-8')),
                    json.load(open(os.path.join(ROOT, 'gt_output', f), encoding='utf-8')), [False])
    return files[f]

log, miss = [], 0
for r, old, new in LINE:
    x = rows[r]; f, i = x['file'], int(x['idx'])
    src, dst, ch = load(f)
    m = dst[i]['message']
    if old not in m:
        print('MISS', r, i, repr(old), '|', m[:60].replace('\n', '⏎')); miss += 1; continue
    dst[i]['message'] = m.replace(old, new, 1); ch[0] = True
    log.append(('line', f, i, m, dst[i]['message']))
for p in glob.glob(os.path.join(ROOT, 'gt_input', '*.json')):
    f = os.path.basename(p); src, dst, ch = load(f)
    for i, (a, b) in enumerate(zip(src, dst)):
        m0 = m = b.get('message', '')
        for t, o, n in TERM:
            if t in a.get('message', ''):
                m = m.replace(o, n)
        if m != m0:
            b['message'] = m; ch[0] = True; log.append(('auto', f, i, m0, m))
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
with open(os.path.join(ROOT, 'review', '_apply_tone_log.tsv'), 'w', encoding='utf-8') as fo:
    for k, f, i, a, b in log:
        fo.write('%s\t%s\t%d\t%s\t%s\n' % (k, f, i, a.replace('\n', '⏎'), b.replace('\n', '⏎')))
print('changed', len(log), 'auto', sum(l[0] == 'auto' for l in log), 'files', n, 'miss', miss, 'DRY' if DRY else '')
