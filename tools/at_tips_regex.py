"""Regex translations for loading-screen Tips that match whatever line breaks the game uses.
The game re-wraps Tips texts, and with FromLanguage=ja-JP (needed so English UI is translated)
AT merges lines with spaces, so neither the plain key nor the no-newline variant matches.
For each Tips text we have a translation for, allow optional whitespace between all characters.
usage: python -I tools/at_tips_regex.py work/ja_ui_research/ja_map.tsv UI_JA_TXT OUT_FILE"""
import csv, re, sys
sys.stdout.reconfigure(encoding='utf-8')
jamap, uija, out = sys.argv[1:4]
SEP = re.compile(r'(?<!\\)=')
DEC = {'n': '\n', 'r': '\r', 't': '\t', '=': '=', '\\': '\\'}
decode = lambda s: re.sub(r'\\(.)', lambda m: DEC.get(m.group(1), '\\' + m.group(1)), s)
squash = lambda s: re.sub(r'\s+', '', s)

tr = {}
for line in open(uija, encoding='utf-8'):
    line = line.rstrip('\n')
    m = SEP.search(line)
    if m and not line.startswith(('#', 'r:')):
        tr.setdefault(squash(decode(line[:m.start()])), line[m.end():])

def esc(c):
    if c in '\\.^$|?*+()[]{}': return '\\' + c
    if c == '=': return '\\x3D'
    if c == '"': return '\\x22'
    return c

PARTICLE = re.compile(r'(\S+) ([^ \\]+)\\n(의|을|를|이|가|은|는|에|에서|로|으로|와|과|도|만)(?=[ .,!?…]|\\n|$)')
def fix_breaks(v):
    # the ja line breaks were copied into the ko text; a line starting with a bare particle
    # ("아발란치\n의 작전") reads badly, so break before that word instead
    return PARTICLE.sub(lambda m: '%s\\n%s%s' % (m.group(1), m.group(2), m.group(3)), v)

rows, miss = [], 0
for r in csv.reader(open(jamap, encoding='utf-8'), delimiter='\t'):
    if len(r) < 3 or r[0] != 'Tips' or not r[2].strip():
        continue
    key = squash(r[2])
    if key not in tr:
        miss += 1; continue
    pat = '\\s*'.join(esc(c) for c in key)
    rows.append('r:"^%s$"=%s' % (pat, fix_breaks(tr[key]).replace('$', '$$')))
open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(rows) + '\n')
print('tips regex', len(rows), 'no translation', miss, '->', out)
