"""Disassemble a function and resolve RIP-relative metadata usage slots to string literals.
In il2cpp v27+ an uninitialized slot holds an encoded token: ((type << 29) | (index << 1) | 1),
type 5 = string literal.
usage: python disasm_lits.py RVA LENGTH"""
import sys, struct, re, os
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

GA = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC\GameAssembly.dll"
LIT = os.path.join(os.path.dirname(__file__), '..', 'work', 'literals.txt')
lits = {}
for line in open(LIT, encoding='utf-8'):
    i, s = line.rstrip('\n').split('\t', 1)
    lits[int(i)] = s

pe = pefile.PE(GA, fast_load=True)
img = pe.get_memory_mapped_image()
md = Cs(CS_ARCH_X86, CS_MODE_64)
rva, ln = int(sys.argv[1], 16), int(sys.argv[2], 16)
for ins in md.disasm(img[rva:rva + ln], rva):
    note = ''
    m = re.search(r'\[rip ([+-]) 0x([0-9a-f]+)\]', ins.op_str)
    if m:
        tgt = ins.address + ins.size + (int(m.group(2), 16) * (1 if m.group(1) == '+' else -1))
        if tgt + 8 <= len(img):
            v = struct.unpack_from('<Q', img, tgt)[0]
            if v & 1 and v < 1 << 32:
                typ, idx = (v >> 29) & 7, (v & 0x1FFFFFFF) >> 1
                note = f'  ; usage type={typ} idx={idx}'
                if typ == 5:
                    note += ' ' + lits.get(idx, '?')
    print(f'{ins.address:8x}  {ins.mnemonic:6} {ins.op_str}{note}')
