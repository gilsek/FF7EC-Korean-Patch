"""Normalize Japanese-style punctuation left in GalTransl output (in place, keeps a .orig copy once).
「」→“” , full-width ！？：；（）, digits/latin, space → half-width. 『』, ……, ―― are kept.
usage: python gt_postfix.py PROJECT_DIR"""
import glob, json, os, re, shutil, sys

TABLE = {ord('「'): '“', ord('」'): '”', ord('！'): '!', ord('？'): '?', ord('：'): ':', ord('；'): ';',
         ord('（'): '(', ord('）'): ')', ord('　'): ' ', ord('～'): '~', ord('，'): ', ', ord('．'): '.'}
TABLE.update({c: chr(c - 0xFEE0) for c in range(0xFF10, 0xFF1A)})   # ０-９
TABLE.update({c: chr(c - 0xFEE0) for c in range(0xFF21, 0xFF3B)})   # Ａ-Ｚ
TABLE.update({c: chr(c - 0xFEE0) for c in range(0xFF41, 0xFF5B)})   # ａ-ｚ


def fix(s):
    s = s.translate(TABLE)
    s = re.sub(r'“\s*“', '“', s)   # 「“…” -> “…” (model already converted, then 「 added again)
    s = re.sub(r'”\s*”', '”', s)
    return re.sub(r', (?=\n|$)', ',', s)


def main(proj):
    n = 0
    for p in glob.glob(os.path.join(proj, 'gt_output', '*.json')):
        d = json.load(open(p, encoding='utf-8'))
        changed = False
        for x in d:
            m = x.get('message')
            if isinstance(m, str) and fix(m) != m:
                x['message'] = fix(m); changed = True; n += 1
        if changed:
            if not os.path.exists(p + '.orig'):
                shutil.copy2(p, p + '.orig')
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('normalized messages', n)


if __name__ == '__main__':
    main(sys.argv[1])
