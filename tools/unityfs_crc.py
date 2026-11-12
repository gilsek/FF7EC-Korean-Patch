"""Parse a UnityFS bundle: print header and CRC32 candidates (uncompressed data, files).
usage: python unityfs_crc.py BUNDLE [obfuscation-name]"""
import struct, sys, zlib, os
import lz4.block
sys.path.insert(0, os.path.dirname(__file__))
import octo


def parse(d):
    i = d.index(b'\0') + 1
    ver = struct.unpack('>I', d[i:i + 4])[0]; i += 4
    i = d.index(b'\0', i) + 1; i = d.index(b'\0', i) + 1
    size, csz, usz, flags = struct.unpack('>qIII', d[i:i + 20]); i += 20
    if ver >= 7:
        i = (i + 15) & ~15
    if flags & 0x80:
        bi = d[size - csz: size]  # at end (not handled for data offset)
    else:
        bi = d[i:i + csz]; i += csz
    if flags & 0x3F in (2, 3):
        bi = lz4.block.decompress(bi, uncompressed_size=usz)
    if flags & 0x200:
        i = (i + 15) & ~15
    h = bi[:16]; n = struct.unpack('>I', bi[16:20])[0]; p = 20
    blocks = []
    for _ in range(n):
        u, c, fl = struct.unpack('>IIH', bi[p:p + 10]); p += 10; blocks.append((u, c, fl))
    data = bytearray()
    for u, c, fl in blocks:
        chunk = d[i:i + c]; i += c
        data += lz4.block.decompress(chunk, uncompressed_size=u) if fl & 0x3F in (2, 3) else chunk
    nf = struct.unpack('>I', bi[p:p + 4])[0]; p += 4
    files = []
    for _ in range(nf):
        off, sz, fl = struct.unpack('>qqI', bi[p:p + 20]); p += 20
        e = bi.index(b'\0', p); nm = bi[p:e].decode(); p = e + 1
        files.append((nm, off, sz))
    return dict(ver=ver, size=size, flags=flags, hash=h, blocks=blocks, data=bytes(data), files=files, end=i)


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    if len(sys.argv) > 2:
        d = octo.deobfuscate(d, sys.argv[2])
    r = parse(d)
    print('ver', r['ver'], 'size', r['size'], 'len', len(d), 'dataend', r['end'], 'flags', hex(r['flags']), 'blocks', r['blocks'])
    print('hash128', r['hash'].hex())
    print('crc data', zlib.crc32(r['data']), 'crc whole', zlib.crc32(d))
    for nm, off, sz in r['files']:
        print(' file', nm, off, sz, 'crc', zlib.crc32(r['data'][off:off + sz]))
