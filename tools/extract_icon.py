"""Extract the main icon group of a Windows exe into a .ico file (for the launcher icon).
usage: python -I tools/extract_icon.py FF7EC.exe launcher/ff7ec.ico"""
import struct, sys
import pefile

exe, out = sys.argv[1], sys.argv[2]
pe = pefile.PE(exe)
RT_ICON, RT_GROUP_ICON = 3, 14
icons, groups = {}, []
for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    for e in t.directory.entries:
        for lang in e.directory.entries:
            data = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
            if t.id == RT_ICON:
                icons[e.id] = data
            elif t.id == RT_GROUP_ICON:
                groups.append(data)
g = groups[0]
_, _, count = struct.unpack_from('<HHH', g, 0)
entries, blobs = [], []
for i in range(count):
    w, h, cc, r, planes, bpp, size, nid = struct.unpack_from('<BBBBHHIH', g, 6 + i * 14)
    entries.append((w, h, cc, r, planes, bpp, icons[nid]))
off = 6 + 16 * count
hdr = struct.pack('<HHH', 0, 1, count)
body = b''
for w, h, cc, r, planes, bpp, d in entries:
    hdr += struct.pack('<BBBBHHII', w, h, cc, r, planes, bpp, len(d), off + len(body))
    body += d
open(out, 'wb').write(hdr + body)
print('icons', count, [(w or 256, bpp) for w, h, cc, r, p, bpp, d in entries], '->', out)
