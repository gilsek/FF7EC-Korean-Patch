"""Fill story rows whose en source is punctuation only (so they never went to GalTransl) but ja has text.
Edits work/tl_v2/story_ko.tsv in place, only rows whose ko column is empty. Run right after gt_import.
usage: python -I tools/story_manual_fill.py"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = os.path.join(B, 'work', 'tl_v2', 'story_ko.tsv')
FILL = {
    'TXT_FF7_MAIN_03_010008_01_095': '……읏!',
    'TXT_FF7_MAIN_02_010004_01_072': '……2,000이다!',
    'TXT_FF7_MAIN_13_010060_01_039': '……읏!?',
    'TXT_CC_MAIN_01_020128_01_006': '――읏차',
    'TXT_FS2_MAIN_06_040376_01_008': '하지만……',
    'TXT_FS_MAIN_18_030212_01_002': '멍멍!',
    'TXT_DC_MAIN_02_903704_01_010': '……읏!',
    'TXT_DC_MAIN_02_903707_01_028': '어, 눈물……?',
}
lines = open(P, encoding='utf-8', newline='').read().split('\n')
h = lines[0].split('\t'); ik = h.index('ko'); n = 0
for i, l in enumerate(lines[1:], 1):
    f = l.split('\t')
    if len(f) == len(h) and f[0] in FILL and not f[ik]:
        f[ik] = FILL[f[0]]; lines[i] = '\t'.join(f); n += 1
open(P, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
print('filled', n)
