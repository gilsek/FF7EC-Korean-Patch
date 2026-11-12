"""Dump il2cpp (metadata v31) string literals to a text file, one per line: index<TAB>repr.
usage: python literals.py global-metadata.dat out.txt"""
import struct, sys

d = open(sys.argv[1], 'rb').read()
lit_off, lit_size, data_off, data_size = struct.unpack_from('<4I', d, 8)
n = lit_size // 8
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    for i in range(n):
        length, idx = struct.unpack_from('<2I', d, lit_off + i * 8)
        s = d[data_off + idx: data_off + idx + length].decode('utf-8', 'replace')
        f.write(f'{i}\t{s!r}\n')
print(n, 'literals')
