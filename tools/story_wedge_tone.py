"""Wedge's 'っす' -> '~슈' everywhere (guideline). DeepSeek mixed in '~임다' on half of his lines.
Only touches lines whose speaker name is Wedge. Hand-written replacements.
usage: python -I tools/story_wedge_tone.py"""
import glob, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REP = [
    ('가면 됨다!', '가슈!'), ('또 먹고 싶음다', '또 먹고 싶슈'), ('받고 싶임다', '받고 싶슈'),
    ('이렇게 되는 거임다', '이렇게 되는 거슈'), ('같이, 오자임다', '같이, 오자슈'), ('본 애임다.', '본 애슈.'),
    ('힘낼 거임다!', '힘내겠슈!'), ('출발하는 거임다', '출발이슈'), ('가짜임다!', '가짜슈!'),
    ('어떻게 해주실 거임다!?', '어떻게 해줄 거슈!?'), ('다행임다', '다행이슈'), ('큰일임다', '큰일이슈'),
    ('이쪽임다', '이쪽이슈'), ('매진임다', '매진이슈'), ('물론임다', '물론이슈'), ('기다리고 있겠임다', '기다리고 있겠슈'),
    ('20개임다', '20개슈'), ('덕분임다', '덕분이슈'), ('만나러 가는 거임다', '만나러 가는 거슈'),
    ('대성황임다', '대성황이슈'), ('금물임다', '금물이슈'), ('22개 주세요임다', '22개 주슈'),
    ('한 그릇 더임다~!', '한 그릇 더~!'), ('못 하는 거임다', '못 하는 거슈'), ('만두, 있어임다', '만두, 있슈'),
    ('마황의 샘임다', '마황의 샘이슈'), ('집합임다', '집합이슈'), ('죄송함다……슈', '죄송하……슈'), ('확보해 둘게슈', '확보해 두겠슈'),
]
n = 0; used = set()
for p in glob.glob(os.path.join(B, 'gt_project_v2', 'gt_input', '*.json')):
    I = json.load(open(p, encoding='utf-8')); q = p.replace('gt_input', 'gt_output')
    O = json.load(open(q, encoding='utf-8')); ch = False
    for a, b in zip(I, O):
        if a.get('name') != 'Wedge': continue
        s = b['message']
        for old, new in REP:
            if old in s: s = s.replace(old, new); used.add(old)
        if s != b['message']:
            b['message'] = s; ch = True; n += 1
    if ch:
        json.dump(O, open(q, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n, 'unused:', [o for o, _ in REP if o not in used])
