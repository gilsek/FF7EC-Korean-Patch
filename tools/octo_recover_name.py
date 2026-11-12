"""Recover the asset bundle name (XOR key) of an octo file from known UnityFS plaintext.
mask(name): m[2i]=name[i], m[2L-1-2i]=name[i]; then every byte ^= h, h = rot-hash of m.
cipher[pos] = plain[pos] ^ m[pos % 2L] for pos>=1 (pos 0 = type byte)."""
import hashlib, os, sys, glob

KNOWN = b'UnityFS\x00\x00\x00\x00\x085.x.x\x002021.3.58f'


def make_mask(name: bytes) -> bytes:
    L = len(name)
    m = bytearray(2 * L)
    for i, c in enumerate(name):
        m[2 * i] = c
        m[2 * L - 1 - 2 * i] = c
    h = 0xAB
    for b in m:
        h = (((h & 1) << 7) | (h >> 1)) ^ b
    return bytes(x ^ (h & 0xFF) for x in m)


def recover(blob):
    ks = {p: blob[p] ^ KNOWN[p] for p in range(1, len(KNOWN))}
    out = []
    for L in range(1, 40):
        n = 2 * L
        for h in range(256):
            name = [None] * L
            ok = True
            for p, k in ks.items():
                j = p % n
                c = k ^ h
                i = j // 2 if j % 2 == 0 else L - 1 - (j - 1) // 2
                if name[i] is not None and name[i] != c:
                    ok = False; break
                name[i] = c
            if not ok or None in name:
                continue
            nm = bytes(name)
            if all(32 < c < 127 for c in nm):
                m = make_mask(nm)
                if all(m[p % n] == ks[p] for p in ks):
                    out.append(nm.decode())
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        b = open(p, 'rb').read(64)
        print(os.path.basename(os.path.dirname(p)), os.path.basename(p), 'type', b[0], recover(b))
