"""Cait Sith: FF7 Rebirth official Korean renders his Kansai-ben as standard polite speech (습니다/요).
DeepSeek used a pseudo-dialect (~심다/~임다/~됨다) on some lines; normalize those. Exact old->new per line.
usage: python -I tools/story_caitsith_tone.py"""
import glob, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FIX = {
    '하이데커가\n여러분을 노리고 있슴다.': '하이데커가\n여러분을 노리고 있습니다.',
    '얕보면 안 되심다!\n잃어버린 물건, 실종자, 뭐든지 가능하심다!': '얕보면 안 됩니다!\n잃어버린 물건, 실종자, 뭐든지 찾아 드립니다!',
    '자, 그럼 가 보겠심다!!': '자, 그럼 가 보겠습니다!!',
    '저, 캐트시 2호기임다~\n잘 부탁드림다~!': '저, 캐트시 2호기입니다~\n잘 부탁드립니다~!',
    '뭐야 이건……\n난 이런 건 처음 봤심다': '뭡니까 이건……\n저, 이런 건 처음 봤습니다',
    '도우러 왔심다!': '도우러 왔습니다!',
    '사형에는 반대임다.\n이 여자도 싫고 말임다.': '사형에는 반대입니다.\n이 여자도 싫고 말이죠.',
    '자, 얼른 티파 양을 구해야죠――\n입구는 제가 지키고 있겠심다!': '자, 얼른 티파 씨를 구해야죠――\n입구는 제가 지키고 있겠습니다!',
    '어쩔 수 없심다, 작전 변경임다!\n공항까지 달려야 됨다!': '어쩔 수 없네요, 작전 변경입니다!\n공항까지 달립시다!',
    '됐심다, 됐심다!\n이렇게 된 바엔 한번 걸어 봐야 됨다!': '됐어요, 됐어요!\n이렇게 된 이상 모 아니면 도입니다!',
    '미드가르 사람들한테\n일단 피난해 달라고 하고 있심다.': '미드가르 사람들한테는\n일단 피난해 달라고 해 뒀습니다.',
    '죄송하지만\n이 가짜 몸으로\n열심히 해 보겠심다.': '죄송하지만\n이 가짜 몸으로\n열심히 해 보겠습니다.',
    '원장님한테는\n당해낼 수 없구먼': '원장님한테는\n당해낼 수가 없네요',
}
n = 0; used = set()
for p in glob.glob(os.path.join(B, 'gt_project_v2', 'gt_input', '*.json')):
    I = json.load(open(p, encoding='utf-8')); q = p.replace('gt_input', 'gt_output')
    O = json.load(open(q, encoding='utf-8')); ch = False
    for a, b in zip(I, O):
        if a.get('name') != 'Cait Sith': continue
        if b['message'] in FIX:
            used.add(b['message']); b['message'] = FIX[b['message']]; ch = True; n += 1
    if ch:
        json.dump(O, open(q, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n, 'unused:', [k for k in FIX if k not in used])
