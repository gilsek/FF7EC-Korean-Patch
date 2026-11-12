"""Make a ui_ko TSV keyed by the real Japanese text (from work/ja_ui_research/ja_map.tsv,
built-in ja catalog matched to LocalizeText ids). Only rows with Japanese text are kept.
usage: python ui_jamap.py JA_MAP.tsv UI_KO.tsv OUT.tsv"""
import csv, re, sys
from build_tl_tables import esc

JP = re.compile(r'[぀-ヿ一-鿿]')


def main(ja_map, ui_ko, dst):
    m = {(x['en_file'], str(x['id'])): x['ja']
         for x in csv.DictReader(open(ja_map, encoding='utf-8'), delimiter='\t')}
    rows = list(csv.reader(open(ui_ko, encoding='utf-8'), delimiter='\t'))
    h = rows[0]; fi, ii, ei = h.index('file'), h.index('id'), h.index('en')
    out = [h]
    for r in rows[1:]:
        j = m.get((r[fi], str(r[ii])))
        if j and JP.search(j):
            r = list(r); r[ei] = esc(j); out.append(r)
    with open(dst, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n').writerows(out)
    print('ja rows', len(out) - 1)


if __name__ == '__main__':
    main(*sys.argv[1:4])
