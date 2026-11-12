"""Build a ui_ko TSV whose en column holds the text the Japanese client actually shows.
save\\LocalizeText\\Ja from the fan server is English (ja==en for every row), so the real Japanese
comes only from the built-in StreamingAssets ja catalog. Rows with a Japanese built-in value get it as key;
the rest keep the English key (the client shows those as served).
usage: python ui_jakey.py UI_KO.tsv OUT.tsv"""
import csv, re, sys
import build_tl_tables as b

JP = re.compile(r'[぀-ヿ一-鿿]')


def main(src, dst):
    bi = b.ja_ui_builtin()
    rows = list(csv.reader(open(src, encoding='utf-8'), delimiter='\t'))
    h = rows[0]; fi, ii, ei = h.index('file'), h.index('id'), h.index('en')
    n = 0
    for r in rows[1:]:
        j = bi.get(r[fi], {}).get(str(r[ii]))
        if j and JP.search(j):
            r[ei] = b.esc(j); n += 1
    with open(dst, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n').writerows(rows)
    print('rows', len(rows) - 1, 'ja keys', n)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
