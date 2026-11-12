"""Print printable ASCII strings in a binary file matching a regex.
usage: python strs.py FILE REGEX [minlen]"""
import re, sys

data = open(sys.argv[1], 'rb').read()
pat = re.compile(sys.argv[2].encode(), re.I)
minlen = int(sys.argv[3]) if len(sys.argv) > 3 else 5
seen = set()
for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data):
    s = m.group()
    if pat.search(s) and s not in seen:
        seen.add(s)
        print(hex(m.start()), s.decode()[:200])
