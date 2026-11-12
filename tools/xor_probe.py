import os, sys, glob, hashlib
O = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC\octo\v1\3001"
known = b'UnityFS\x00\x00\x00\x00\x085.x.x\x002021.3.58f'
files = [p for p in glob.glob(os.path.join(O, '0', '*', '*')) if not p.endswith('.meta')][:6]
for p in files:
    b = open(p, 'rb').read()
    for skip in (1,):
        ks = bytes(x ^ y for x, y in zip(b[skip:skip + len(known)], known))
        name = os.path.basename(p)
        print(os.path.basename(os.path.dirname(p)), name, len(b), 'type', b[0], ks.hex())
        print('   ks ascii:', ''.join(chr(c) if 32 <= c < 127 else '.' for c in ks))
        print('   md5name:', bytes.fromhex(name)[:16].hex())
