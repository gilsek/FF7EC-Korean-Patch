"""Add newline-free key variants for AutoTranslator text files.
The game re-wraps some UI text (loading tips etc.) with different line breaks, and AT
(IgnoreWhitespaceInDialogue=True) then looks up the key with all line breaks removed.
Our keys keep the master-data breaks, so they never match. This writes extra lines
`<key without \\n/\\r>=<same translation>` for every key that contains a break.
usage: python -I tools/at_nows_variants.py TEXT_DIR OUT_FILE"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
d, out = sys.argv[1], sys.argv[2]
have, items = set(), []
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.txt') or fn.startswith('_') or os.path.abspath(os.path.join(d, fn)) == os.path.abspath(out):
        continue
    for line in open(os.path.join(d, fn), encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#') or line.startswith('r:') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        have.add(k)
        items.append((k, v))
seen, rows = set(), []
for k, v in items:
    if '\\n' not in k and '\\r' not in k:
        continue
    # walk AT escapes pairwise so an escaped backslash (\\\\n = literal '\' + 'n') is kept
    s = re.sub(r'\\.', lambda m: '' if m.group() in ('\\n', '\\r') else m.group(), k)
    if s == k:
        continue
    if len(s) < 20 or s in have or s in seen:   # AT applies IgnoreWhitespace only at MinDialogueChars=20+
        continue
    seen.add(s); rows.append('%s=%s' % (s, v))
open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(rows) + '\n')
print('variants', len(rows), '->', out)
