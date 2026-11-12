"""Check FontPatch output against the pristine files with UnityPy.
usage: python -I patcher/FontPatch/verify.py PATCHED_GAME_DIR ORIG_DIR(backup/orig) FONT [HUD_FONT]"""
import base64, json, sys
import UnityPy
sys.stdout.reconfigure(encoding='utf-8')
g, o, fontp = sys.argv[1:4]
font = open(fontp, 'rb').read()
hud = open(sys.argv[4], 'rb').read() if len(sys.argv) > 4 else font
AA = g + r'\FF7EC_Data\StreamingAssets\aa'
H = '81246fb8f207e1016fff88f97a64e241'
pairs = [(AA + r'\StandaloneWindows64\font_assets_assets\command\internalassets\font\fot-skippron-d.otf_%s.bundle' % H, o + r'\01_fot-skippron-d.otf_%s.bundle' % H, None),
         (g + r'\FF7EC_Data\data.unity3d', o + r'\data.unity3d', 'FOT-SkipProN-D')]
ok = True
def objs(p):
    env = UnityPy.load(p); r = {}
    for name, f in env.file.files.items():
        if hasattr(f, 'objects'):
            r[name] = {pid: ob.type.name for pid, ob in f.objects.items()}
        else:
            r[name] = None
    return env, r
for new, old, name in pairs:
    en, rn = objs(new); eo, ro = objs(old)
    same = rn == ro
    fonts = 0
    for ob_n in en.objects:
        if ob_n.type.name != 'Font': continue
        fn = ob_n.read()
        ob_o = [x for x in eo.objects if x.path_id == ob_n.path_id and x.assets_file.name == ob_n.assets_file.name][0].read()
        d_new, d_old = bytes(fn.m_FontData), bytes(ob_o.m_FontData)
        if name is None or fn.m_Name == name:
            fonts += 1; good = d_new == (hud if name else font)
        else:
            good = d_new == d_old
        print(' ', fn.m_Name, 'ok' if good else 'MISMATCH', len(d_new)); ok &= good
    # raw resS / other files byte-equal
    for k, f in en.file.files.items():
        if not hasattr(f, 'objects'):
            a = bytes(f.bytes) if hasattr(f, 'bytes') else None
            b = bytes(eo.file.files[k].bytes) if hasattr(eo.file.files[k], 'bytes') else None
            if a != b: print('  resource differs', k); ok = False
    print(new[-40:], 'structure', 'same' if same else 'DIFF', 'target fonts', fonts); ok &= same and fonts == 1
c_new = open(AA + r'\catalog.json', 'rb').read(); c_old = open(o + r'\00_catalog.json', 'rb').read()
diff = [i for i in range(len(c_old)) if c_new[i] != c_old[i]] if len(c_new) == len(c_old) else None
j = json.loads(c_new); ex = base64.b64decode(j['m_ExtraDataString'])
key = ('"m_Hash":"%s","m_Crc":' % H).encode('utf-16-le'); i = ex.find(key) + len(key)
crc = ex[i:ex.find(','.encode('utf-16-le'), i)].decode('utf-16-le')
print('catalog len same', diff is not None, 'diff bytes', len(diff) if diff else 0, 'crc', repr(crc))
ok &= diff is not None and 0 < len(diff) < 20 and crc.strip() == '0'
print('ALL OK' if ok else 'FAIL')
