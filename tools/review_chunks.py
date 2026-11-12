"""Split a GalTransl project's input/output into compact review chunks for agent-based review.
usage: python review_chunks.py PROJECT_DIR [--rows 500]
-> PROJECT_DIR/review/chunks/chunk_NNN.txt  (header line '## <file>' then 'idx<TAB>name<TAB>ja<TAB>ko', newlines as ⏎)
   PROJECT_DIR/review/chunks/index.tsv     (chunk, file, first_idx, last_idx)"""
import glob, json, os, sys

proj = sys.argv[1]
rows_per = int(sys.argv[sys.argv.index('--rows') + 1]) if '--rows' in sys.argv else 500
out = os.path.join(proj, 'review', 'chunks')
os.makedirs(out, exist_ok=True)
nl = lambda s: str(s).replace('\r', '').replace('\n', '⏎').replace('\t', ' ')

chunks, cur, n = [], [], 0
for ip in sorted(glob.glob(os.path.join(proj, 'gt_input', '*.json'))):
    f = os.path.basename(ip)
    src = json.load(open(ip, encoding='utf-8'))
    dst = json.load(open(os.path.join(proj, 'gt_output', f), encoding='utf-8'))
    if n and n + len(src) > rows_per:
        chunks.append(cur); cur, n = [], 0
    cur.append((f, src, dst)); n += len(src)
if cur: chunks.append(cur)

with open(os.path.join(out, 'index.tsv'), 'w', encoding='utf-8') as ix:
    for ci, ch in enumerate(chunks):
        name = 'chunk_%03d' % ci
        with open(os.path.join(out, name + '.txt'), 'w', encoding='utf-8') as fo:
            for f, src, dst in ch:
                fo.write('## %s\n' % f)
                for i, (a, b) in enumerate(zip(src, dst)):
                    fo.write('%d\t%s\t%s\t%s\n' % (i, nl(a.get('name', '')), nl(a.get('message', '')), nl(b.get('message', ''))))
                ix.write('%s\t%s\t0\t%d\n' % (name, f, len(src) - 1))
print('chunks', len(chunks), 'rows', sum(len(s) for ch in chunks for _, s, _ in ch))
