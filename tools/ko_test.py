"""Korean display test: patch a few UI strings + swap main font data for a Hangul-capable font.
usage: python ko_test.py apply FONT.ttf     (backs up originals to backup/orig first, once)
       python ko_test.py restore
"""
import base64, gzip, hashlib, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
import ff7crypt
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

G = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC"
SA = G + r"\FF7EC_Data\StreamingAssets"
MD = SA + r"\MasterData"
AA = SA + r"\aa"
FONT_BUNDLE = AA + r"\StandaloneWindows64\font_assets_assets\command\internalassets\font\fot-skippron-d.otf_81246fb8f207e1016fff88f97a64e241.bundle"
FONT_HASH = '81246fb8f207e1016fff88f97a64e241'
SRV = G + r"\save\LocalizeText\En"
BK = os.path.join(os.path.dirname(__file__), '..', 'backup', 'orig')
MANIFEST = os.path.join(BK, 'manifest.json')

PATCH = {
    'OutGameTitle': {226004: '터치하여 시작', 226001: '버전'},
    'Common': {100001: '확인', 100002: '취소', 100006: '스토리'},
}

b32 = lambda b: base64.b32encode(b).decode().rstrip('=')


def backup(paths, created):
    if os.path.exists(MANIFEST):
        return
    os.makedirs(BK, exist_ok=True)
    m = {'files': {}, 'created': created}
    for i, p in enumerate(paths):
        dst = os.path.join(BK, f'{i:02d}_' + os.path.basename(p))
        shutil.copy2(p, dst)
        m['files'][dst] = p
    json.dump(m, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def dec_parts(blob):
    gz = unpad(AES.new(ff7crypt.KEY, AES.MODE_CBC, blob[:16]).decrypt(blob[16:]), 16)
    return gz


def patch_text(blob, changes):
    d = json.loads(gzip.decompress(dec_parts(blob)))
    hit = 0
    for x in d['data']:
        if x['id'] in changes:
            x['value'] = changes[x['id']]; hit += 1
    assert hit == len(changes), (hit, changes)
    payload = json.dumps(d, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    enc = ff7crypt.encrypt(payload, blob[:16])
    return enc, b32(hashlib.sha256(dec_parts(enc)).digest()), len(enc)


def apply(font_path):
    idx = json.load(open(MD + r"\index.json", encoding='utf-8'))
    cat_rel = idx['language_catalog_en']
    cat_p = MD + cat_rel.replace('/', '\\')
    srv_cat = SRV + r"\text_catalog.json"
    to_backup = [AA + r"\catalog.json", FONT_BUNDLE, MD + r"\index.json", cat_p, srv_cat] + \
                [SRV + f"\\{n}.json" for n in PATCH]
    created = []
    # --- text: StreamingAssets copy + server copy ---
    cat = json.loads(ff7crypt.decrypt(open(cat_p, 'rb').read()))
    scat_blob = open(srv_cat, 'rb').read()
    scat = json.loads(ff7crypt.decrypt(scat_blob))
    new_files = []
    for name, ch in PATCH.items():
        e = next(x for x in cat['files'] if x['name'] == name)
        # base on the server copy (newer than the built-in StreamingAssets one)
        enc, h, size = patch_text(open(SRV + f"\\{name}.json", 'rb').read(), ch)
        fname = b32(hashlib.sha256(enc).digest()) + '.json'
        newrel = e['path'].rsplit('/', 1)[0] + '/' + fname
        new_files.append((MD + newrel.replace('/', '\\'), enc))
        e.update(hash=h, size=size, path=newrel)
        se = next(x for x in scat['files'] if x['name'] == name)
        se.update(hash=h, size=size, path=newrel)
        new_files.append((SRV + f"\\{name}.json", enc))
    cat_payload = json.dumps(cat, ensure_ascii=False, indent=1).encode('utf-8')
    cat_enc = ff7crypt.encrypt(cat_payload, open(cat_p, 'rb').read()[:16])
    new_cat_rel = '/language_catalogs/en/' + b32(hashlib.sha256(cat_enc).digest()) + '.json'
    scat_enc = ff7crypt.encrypt(json.dumps(scat, ensure_ascii=False, indent=1).encode('utf-8'), scat_blob[:16])
    # --- font ---
    import UnityPy
    env = UnityPy.load(FONT_BUNDLE)
    for o in env.objects:
        if o.type.name == 'Font':
            f = o.read()
            f.m_FontData = list(open(font_path, 'rb').read())
            f.save()
    font_bytes = env.file.save(packer='lz4')
    # --- addressables catalog: zero this bundle's CRC (same-length edit) ---
    cj_path = AA + r"\catalog.json"
    cj = json.load(open(cj_path, encoding='utf-8'))
    ex = bytearray(base64.b64decode(cj['m_ExtraDataString']))
    key = ('"m_Hash":"%s","m_Crc":' % FONT_HASH).encode('utf-16-le')
    i = ex.find(key); assert i > 0
    j = i + len(key)
    k = ex.find(','.encode('utf-16-le'), j)
    digits = (k - j) // 2
    ex[j:k] = ('0' + ' ' * (digits - 1)).encode('utf-16-le')
    cj['m_ExtraDataString'] = base64.b64encode(bytes(ex)).decode()

    backup(to_backup, [p for p, _ in new_files if not os.path.exists(p)] + [MD + new_cat_rel.replace('/', '\\')])
    for p, b in new_files:
        open(p, 'wb').write(b)
    open(MD + new_cat_rel.replace('/', '\\'), 'wb').write(cat_enc)
    idx['language_catalog_en'] = new_cat_rel
    open(MD + r"\index.json", 'w', encoding='utf-8').write(json.dumps(idx, separators=(',', ':')))
    open(srv_cat, 'wb').write(scat_enc)
    open(FONT_BUNDLE, 'wb').write(font_bytes)
    open(cj_path, 'w', encoding='utf-8').write(json.dumps(cj, separators=(',', ':')))
    print('applied. new catalog', new_cat_rel, 'font bundle', len(font_bytes))


def restore():
    m = json.load(open(MANIFEST, encoding='utf-8'))
    for src, dst in m['files'].items():
        shutil.copy2(src, dst)
    for p in m['created']:
        if os.path.exists(p):
            os.remove(p)
    print('restored', len(m['files']), 'files, removed', len(m['created']))


if __name__ == '__main__':
    apply(sys.argv[2]) if sys.argv[1] == 'apply' else restore()
