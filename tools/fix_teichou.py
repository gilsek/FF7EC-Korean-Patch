"""Unify 艇長 (Cid's nickname) to 함장: replace 정장 in lines whose source contains 艇長.
usage: python -I tools/fix_teichou.py FILE [FILE...]   (story.txt uses '=', story_ko.tsv uses tab)"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
for p in sys.argv[1:]:
    raw = open(p, encoding='utf-8', newline='').read()
    out, n = [], 0
    for line in raw.split('\n'):
        sep = '\t' if p.endswith('.tsv') else '='
        if '艇長' in line and sep in line:
            k, v = line.split(sep, 1)
            if '艇長' in k and '정장' in v:
                v = v.replace('정장', '함장'); n += 1
                line = k + sep + v
        out.append(line)
    open(p, 'w', encoding='utf-8', newline='').write('\n'.join(out))
    print(p, 'fixed', n)
