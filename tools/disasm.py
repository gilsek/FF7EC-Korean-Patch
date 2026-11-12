"""Disassemble GameAssembly.dll at RVA. Annotates call targets with method names from a Cpp2IL
diffable-cs (attributeinjector) dump.
usage: python disasm.py RVA LENGTH [RVA LENGTH ...]"""
import os, re, sys, glob, pickle
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

GA = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC\GameAssembly.dll"
DUMP = os.path.join(os.path.dirname(__file__), '..', 'work', 'cpp2il_addr', 'DiffableCs')
CACHE = os.path.join(os.path.dirname(__file__), '..', 'work', 'rva_names.pkl')


def load_names():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    names = {}
    rx = re.compile(r'RVA = "0x([0-9A-F]+)"')
    for p in glob.glob(os.path.join(DUMP, '**', '*.cs'), recursive=True):
        cls = os.path.splitext(os.path.basename(p))[0]
        pending = None
        for line in open(p, encoding='utf-8', errors='replace'):
            m = rx.search(line)
            if m:
                pending = int(m.group(1), 16)
                continue
            s = line.strip()
            if pending is not None and '(' in s and not s.startswith('['):
                names.setdefault(pending, cls + '::' + s.split('(')[0].split()[-1])
                pending = None
    pickle.dump(names, open(CACHE, 'wb'))
    return names


pe = pefile.PE(GA, fast_load=True)
img = pe.get_memory_mapped_image()
names = load_names()
md = Cs(CS_ARCH_X86, CS_MODE_64)
args = sys.argv[1:]
for i in range(0, len(args), 2):
    rva, ln = int(args[i], 16), int(args[i + 1], 16)
    print(f'===== {hex(rva)} {names.get(rva, "?")}')
    for ins in md.disasm(img[rva:rva + ln], rva):
        note = ''
        if ins.mnemonic in ('call', 'jmp') and ins.op_str.startswith('0x'):
            note = '  ; ' + names.get(int(ins.op_str, 16), '')
        print(f'{ins.address:8x}  {ins.mnemonic:6} {ins.op_str}{note}')
