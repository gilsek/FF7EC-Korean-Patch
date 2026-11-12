"""Story dialogue test: replace a few TXT_ lines in one Lua script bundle, re-obfuscate, write back in place.
usage: python story_test.py apply | restore"""
import json, os, re, shutil, sys
import UnityPy
sys.path.insert(0, os.path.dirname(__file__))
import octo

NAME = 'data/dungeoncontentluascript/0001/en/dat_asset_lua_script_map_0001_content_002.a'
LINES = {
    'TXT_FF7_MAIN_01_010001_01_001': r'이쪽이야,\n용병!',
    'TXT_FF7_MAIN_01_010001_01_002': '금방 열 테니까 잠깐만.',
    'TXT_FF7_MAIN_01_010001_01_003': '망 잘 봐, 웨지.',
    'TXT_FF7_MAIN_01_010001_01_004': '알겠어!',
    'TXT_FF7_MAIN_01_010001_01_005': r'마코로가 바로 앞이야. \n밥값 좀 해 봐, 신입.',
}
BK = os.path.join(os.path.dirname(__file__), '..', 'backup', 'story')


def obfuscate(raw: bytes, name: str, typ: int) -> bytes:
    if typ == ord('U'):
        return raw
    out = bytearray(octo.deobfuscate(bytes([typ]) + raw[1:], name))  # xor is its own inverse
    out[0] = typ
    return bytes(out)


def target():
    db = octo.load_db()
    e = next(x for x in db['assetBundleList'] if x['name'] == NAME)
    return octo.disk_path(e)


def apply():
    p = target()
    os.makedirs(BK, exist_ok=True)
    bk = os.path.join(BK, os.path.basename(p))
    if not os.path.exists(bk):
        shutil.copy2(p, bk)
        json.dump({bk: p}, open(os.path.join(BK, 'manifest.json'), 'w'))
    blob = open(bk, 'rb').read()
    env = UnityPy.load(octo.deobfuscate(blob, NAME))
    hit = 0
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        t = o.read()
        s = t.m_Script
        s = s.decode('utf-8') if isinstance(s, bytes) else s
        for k, v in LINES.items():
            s, n = re.subn(r'^(\s*%s\s*=\s*)"(?:[^"\\]|\\.)*"' % re.escape(k),
                           lambda m: m.group(1) + '"' + v.replace('"', '\\"') + '"', s, flags=re.M)
            hit += n
        t.m_Script = s
        t.save()
    assert hit == len(LINES), hit
    raw = forge_crc(env, octo.deobfuscate(blob, NAME))
    open(p, 'wb').write(obfuscate(raw, NAME, blob[0]))
    print('patched', hit, 'lines ->', p, len(blob), '->', os.path.getsize(p))


PH = 'QZQZ' + '\u0001\u0002\u0003\u0004'


def _set_tail(env, tail):
    """Set the trailing Lua comment (replaces previous tail) on the TextAsset with TXT_ lines."""
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        t = o.read()
        s = t.m_Script
        s = s.decode('utf-8') if isinstance(s, bytes) else s
        if 'TXT_' not in s:
            continue
        s = re.sub(r'\n--CRC.{8}$', '', s, flags=re.S)
        t.m_Script = s + '\n--CRC' + tail
        t.save()
        return
    raise RuntimeError('no text asset')


def forge_crc(env, orig_raw):
    """Make CRC32 of the uncompressed bundle data equal the original (Octo/Unity checks it)."""
    import random, zlib
    import unityfs_crc
    target = zlib.crc32(unityfs_crc.parse(orig_raw)['data'])
    _set_tail(env, PH)
    data = unityfs_crc.parse(env.file.save(packer='original'))['data']
    pos = data.index(PH.encode('utf-8'))
    pre, suf = data[:pos], data[pos + 8:]
    rnd = random.Random(1)
    printable = bytes(range(0x21, 0x7F)).replace(b'\\', b'')
    for _ in range(20000):
        head = bytes(rnd.choice(printable) for _ in range(4))
        f = lambda x: zlib.crc32(pre + head + x + suf)
        base = f(bytes(4))
        cols = [f((1 << i).to_bytes(4, 'little')) ^ base for i in range(32)]
        # solve sum(b_i * cols[i]) = base ^ target over GF(2)
        rows = [(cols[i], 1 << i) for i in range(32)]
        basis = {}
        for v, m in rows:
            for bit in sorted(basis, reverse=True):
                if v >> bit & 1:
                    v ^= basis[bit][0]; m ^= basis[bit][1]
            if v:
                hb = v.bit_length() - 1
                basis[hb] = (v, m)
        if len(basis) < 32:
            continue
        need, mask = base ^ target, 0
        for bit in sorted(basis, reverse=True):
            if need >> bit & 1:
                need ^= basis[bit][0]; mask ^= basis[bit][1]
        x = mask.to_bytes(4, 'little')
        if all(c in printable for c in x):
            tail = (head + x).decode('ascii')
            _set_tail(env, tail)
            out = env.file.save(packer='original')
            got = zlib.crc32(unityfs_crc.parse(out)['data'])
            assert got == target, (got, target)
            return out
    raise RuntimeError('crc forge failed')


def restore():
    for bk, p in json.load(open(os.path.join(BK, 'manifest.json'))).items():
        shutil.copy2(bk, p)
    print('restored')


if __name__ == '__main__':
    apply() if sys.argv[1] == 'apply' else restore()
