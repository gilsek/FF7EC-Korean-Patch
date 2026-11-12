"""When an AT key carries literal backslash-n (written `\\\\n` in the file) but the translation uses
the line-break escape `\\n`, rewrite the translation to the same literal form (counts must match).
usage: python -I tools/at_litnl_fix.py FILE..."""
import sys
BS2N = chr(92) * 2 + 'n'
BS1N = chr(92) + 'n'
for p in sys.argv[1:]:
    L = open(p, encoding='utf-8').read().split('\n'); n = 0
    for i, l in enumerate(L):
        if '=' not in l:
            continue
        k, v = l.split('=', 1)
        if BS2N in k and BS2N not in v and k.count(BS2N) == v.count(BS1N):
            L[i] = k + '=' + v.replace(BS1N, BS2N); n += 1
    open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print(p, n)
