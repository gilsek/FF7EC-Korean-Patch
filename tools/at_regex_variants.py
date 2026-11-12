"""Make regex translations for keys with {0}-style placeholders.
The game formats the string before display ("Enhance any weapon 1 time(s)."), so the plain key
"Enhance any weapon {0} time(s)." never matches. AT supports r:"regex"=replacement lines.
usage: python -I tools/at_regex_variants.py TEXT_DIR OUT_FILE"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
d, out = sys.argv[1], sys.argv[2]
SEP = re.compile(r'(?<!\\)=')
PH = re.compile(r'\{(\d+)\}')
DEC = {'n': '\n', 'r': '\r', 't': '\t', '=': '=', '\\': '\\'}

def decode(s):   # AT text-file escapes -> real text
    return re.sub(r'\\(.)', lambda m: DEC.get(m.group(1), '\\' + m.group(1)), s)

def rx_escape(s):
    o = []
    for c in s:
        if c in '\\.^$|?*+()[]{}': o.append('\\' + c)
        elif c == '\n': o.append('\\n')
        elif c == '\r': o.append('\\r')
        elif c == '\t': o.append('\\t')
        elif c == '=': o.append('\\x3D')
        elif c == '"': o.append('\\x22')
        else: o.append(c)
    return ''.join(o)

rows, seen = [], set()
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.txt') or fn.startswith('_') or fn.startswith('zz_'):
        continue
    for line in open(os.path.join(d, fn), encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#') or line.startswith('r:'):
            continue
        m = SEP.search(line)
        if not m:
            continue
        k, v = line[:m.start()], line[m.end():]
        if not PH.search(k) or '\\\\' in k:
            continue
        text = decode(k)
        parts, used, pat = PH.split(text), set(), ''
        for i, p in enumerate(parts):
            if i % 2 == 0:
                pat += rx_escape(p)
            else:
                g = 'g' + p
                pat += ('\\k<%s>' % g) if g in used else ('(?<%s>.+?)' % g)
                used.add(g)
        if not pat.replace('(?<g0>.+?)', '').strip() or pat in seen:
            continue
        if any('{%s}' % n not in k for n in PH.findall(v)):
            continue   # translation uses a placeholder the key lacks
        seen.add(pat)
        rv = PH.sub(lambda mm: '${g%s}' % mm.group(1), v.replace('$', '$$'))
        rows.append('r:"^%s$"=%s' % (pat, rv))
open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(rows) + '\n')
print('regex', len(rows), '->', out)
