"""Check GalTransl output against input: count, newlines, tags/placeholders, leftover kana/kanji, glossary.
usage: python gt_check.py PROJECT_DIR [--show N]   -> writes PROJECT_DIR/_check.tsv, prints summary"""
import collections, csv, glob, json, os, re, sys

TAG = re.compile(r'<[^<>\n]+>|\[[υμ]\]|\{[^{}\n]*\}')
JA = re.compile(r'[぀-ヿ一-鿿]')


def main(proj, show=0):
    gl = []
    for line in open(os.path.join(proj, 'Dict', 'gpt_dict.txt'), encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 2 and p[0]:
            gl.append((p[0], p[1]))
    gl.sort(key=lambda x: -len(x[0]))
    rows, cnt, total = [], collections.Counter(), 0
    for ip in sorted(glob.glob(os.path.join(proj, 'gt_input', '*.json'))):
        name = os.path.basename(ip)
        op = os.path.join(proj, 'gt_output', name)
        src = json.load(open(ip, encoding='utf-8'))
        if not os.path.exists(op):
            cnt['missing_file'] += 1; rows.append((name, '', 'missing_file', '', '')); continue
        dst = json.load(open(op, encoding='utf-8'))
        if len(src) != len(dst):
            cnt['count_mismatch'] += 1; rows.append((name, '', 'count_mismatch', len(src), len(dst))); continue
        for i, (s, d) in enumerate(zip(src, dst)):
            total += 1
            a, b = s['message'], d.get('message', '')
            probs = []
            if not b.strip(): probs.append('empty')
            if a.count('\n') != b.count('\n'): probs.append('newline')
            if sorted(TAG.findall(a)) != sorted(TAG.findall(b)): probs.append('tag')
            if JA.search(TAG.sub('', b).replace('・', '')): probs.append('japanese')
            rest = a
            for k, v in gl:  # longest first; mask matched terms so substrings (セト in セトラ) are not re-checked
                if k in rest:
                    if v not in b:
                        probs.append('gloss:' + k); break
                    rest = rest.replace(k, '\0')
            for p in probs:
                cnt[p.split(':')[0]] += 1
                rows.append((name, i, p, a, b))
    with open(os.path.join(proj, '_check.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['file', 'idx', 'problem', 'src', 'dst'])
        w.writerows(rows)
    print('messages', total, dict(cnt))
    for r in rows[:show]:
        print(r[2], '|', str(r[3]).replace('\n', '⏎')[:60], '|', str(r[4]).replace('\n', '⏎')[:60])


if __name__ == '__main__':
    n = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 0
    main(sys.argv[1], n)
