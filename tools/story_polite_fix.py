"""Story: lines whose ja source is polite (です/ます) but Korean came out casual. Hand-reviewed with context.
Matches by exact ja source and exact old Korean, so re-running is safe.
usage: python -I tools/story_polite_fix.py"""
import glob, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FIX = [  # (ja source startswith, old ko, new ko)
    ('行きましょう！', '가자!', '가요!'),  # Lucrecia to Hojo/Sephiroth scene
    ('そうはいきません', '그렇게는 안 돼\n당신은 살려서 돌려보내지 않겠어', '그렇게는 안 됩니다\n당신은 살려서 돌려보내지 않겠습니다'),
    ('何者かがシスター・レイを', None, '누군가가 시스터 레이를\n본체 조작으로 전환하고 있습니다!\n이쪽에서는 조작할 수 없습니다!'),
    ('私、ジェシーと会ってから', None, '저, 제시를 만난 뒤로\n혼자가 아니라고 생각하고 있어요'),
    ('みんなとの縁を感じました', '모두와의 인연을 느꼈어', '모두와의 인연을 느꼈어요'),
    ('これからも友達でいてください', '앞으로도 친구로 있어 줘', '앞으로도 친구로 있어 주세요'),
    ('はい\nみんな、がんばれよと', None, '네\n다들 힘내라고\n응원해 줬어요'),
    ('そんなことない！\nオルタは私の兄であり', None, '그렇지 않아요!\n오르타는 제 오빠이자 아버지이자 어머니예요!\n제 가장 소중한, 진짜 동료예요!'),
    ('提供情報どおり、敵勢力のリーダーを発見！', None, '제공된 정보대로 적 세력의 리더를 발견!\n지금부터 포획하겠습니다!'),
    ('並の刀では、石壁にこれほど', None, '보통 칼로는 돌벽에 이만큼\n깊은 상처를 낼 수 없을 겁니다'),
    ('魔王様は負けてません！', '마왕님은 지지 않았어!', '마왕님은 지지 않았어요!'),
    ('ぼく達がお手伝いします！', '우리가 도와드릴게!', '저희가 도와드릴게요!'),
    ('調査を始めましょう。\nアリッサ、手引きをお願いします。', None, '조사를 시작합시다.\n앨리사, 안내를 부탁합니다.'),
    ('少しだけ……時間をください。', '잠시만…… 시간을 주게.', '잠시만…… 시간을 주세요.'),
    ('リーブ・トゥエスティ……', None, '리브 투에스티……\n마침 잘됐군요\n당신도 여기서 소거하겠습니다'),
]
n = 0; hit = [0] * len(FIX)
for p in glob.glob(os.path.join(B, 'gt_project_v2', 'gt_input', '*.json')):
    I = json.load(open(p, encoding='utf-8')); q = p.replace('gt_input', 'gt_output')
    O = json.load(open(q, encoding='utf-8')); ch = False
    for a, b in zip(I, O):
        for fi, (src, old, new) in enumerate(FIX):
            if not a['message'].startswith(src): continue
            if old is not None and b['message'] != old: continue
            if new.count('\n') != a['message'].rstrip('\n').count('\n') and old is None:
                print('LINES', fi, repr(a['message']), repr(b['message'])); continue
            if b['message'] != new:
                b['message'] = new; ch = True; n += 1; hit[fi] += 1
    if ch:
        json.dump(O, open(q, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n, hit)
