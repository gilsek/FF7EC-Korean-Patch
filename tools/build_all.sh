cd "$(dirname "$0")/.."; set -e
python -I tools/gt_import.py gt_project_v2 --tl-dir work/tl_v2 --overwrite 2>&1 | tail -2
python -I tools/story_manual_fill.py
python -I -c "
import sys,csv,os;sys.stdout.reconfigure(encoding='utf-8');sys.path.insert(0,'tools')
csv.field_size_limit(10**8)
src='work/tl_v2/story_ko.tsv';dst='work/tl_v2/story_ko_jakey.tsv'
rows=list(csv.reader(open(src,encoding='utf-8',newline=''),delimiter='\t',quoting=csv.QUOTE_NONE))
h=rows[0];ie,ij=h.index('en'),h.index('ja');n=0
for r in rows[1:]:
  if r[ij]: r[ie]=r[ij];n+=1
w=csv.writer(open(dst,'w',encoding='utf-8',newline=''),delimiter='\t',quoting=csv.QUOTE_NONE,escapechar=None,quotechar='\x01',lineterminator='\n')
w.writerows(rows);print('jakey rows',n)
import make_story_keys as m
m.IN_PATH=os.path.abspath(src);m.OUT_PATH=os.path.abspath('work/storyko_v2/story_ko.tsv');m.main()
" 2>&1 | tail -2
python -I tools/make_at_files.py work/at_out_v2_ja --story work/tl_v2/story_ko_jakey.tsv --ui work/tl/ui_ko.tsv 2>&1 | grep -A3 "요약"
python -I tools/ui_ja_import.py work/ja_ui_research/ja_map.tsv gt_project_ui_ja work/tl_ui_ja/ui_ja_ko.tsv 2>&1 | tail -2
python -I tools/gt_import.py gt_project_ui_v2 --tl-dir work/tl_ui_v2 --overwrite 2>&1 | tail -2
python -I - <<'EOF'
import csv,sys;csv.field_size_limit(10**9);sys.stdout.reconfigure(encoding='utf-8')
ko={}
for x in csv.DictReader(open('work/tl_ui_ja/ui_ja_ko.tsv',encoding='utf-8'),delimiter='\t'):
    ko[(x['file'],x['id'])]=x['ko']
rows=list(csv.reader(open('work/tl_ui_new/ui_ko_jamap.tsv',encoding='utf-8'),delimiter='\t',quoting=csv.QUOTE_NONE))
n=miss=0
for r in rows[1:]:
    k=ko.get((r[0],r[1]))
    if k: r[4]=k.replace('\t',' ').replace('\r','\\r').replace('\n','\\n'); n+=1
    else: miss+=1
with open('work/tl_ui_ja/ui_ko_jamap_v2.tsv','w',encoding='utf-8',newline='') as f:
    for r in rows: f.write('\t'.join(r)+'\n')
print('set',n,'miss',miss)
EOF
python -I tools/make_at_files.py work/at_ui_v2 --ui work/tl_ui_v2/ui_ko.tsv 2>&1 | grep -A3 "요약"
python -I tools/make_at_files.py work/at_ui_ja_v2 --ui work/tl_ui_ja/ui_ko_jamap_v2.tsv 2>&1 | grep -A3 "요약"
python -I tools/at_litnl_fix.py work/at_ui_ja_v2/ui.txt work/at_ui_v2/ui.txt 2>&1 | tail -2
wc -l work/at_out_v2_ja/story.txt work/storyko_v2/story_ko.tsv work/at_ui_v2/ui.txt work/at_ui_ja_v2/ui.txt
for w in '휴지 메가 수박' '얼티마' '데미지' '화염 속성' '탐브린'; do printf "%s: " "$w"; cat work/at_out_v2_ja/story.txt work/storyko_v2/story_ko.tsv work/at_ui_v2/ui.txt work/at_ui_ja_v2/ui.txt | grep -c "$w" || true; done