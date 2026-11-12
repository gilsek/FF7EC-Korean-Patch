"""Swap the game's main font data (FOT-Skip ProN D bundle) for another font file.
Always starts from the pristine bundle in backup/orig; catalog CRC was already zeroed by ko_test.py.
usage: python font_swap.py FONT.(otf|ttf)"""
import os, shutil, sys
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
G = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC"
NAME = "fot-skippron-d.otf_81246fb8f207e1016fff88f97a64e241.bundle"
DST = G + r"\FF7EC_Data\StreamingAssets\aa\StandaloneWindows64\font_assets_assets\command\internalassets\font" + "\\" + NAME
ORIG = os.path.join(HERE, '..', 'backup', 'orig', '01_' + NAME)
PREV = os.path.join(HERE, '..', 'backup', 'font_prev')


def main(font):
    env = UnityPy.load(ORIG)
    n = 0
    for o in env.objects:
        if o.type.name == 'Font':
            f = o.read()
            f.m_FontData = list(open(font, 'rb').read())
            f.save(); n += 1
    assert n == 1, n
    data = env.file.save(packer='lz4')
    os.makedirs(PREV, exist_ok=True)
    shutil.copy2(DST, os.path.join(PREV, NAME))   # the bundle that was installed before this run
    open(DST, 'wb').write(data)
    print('swapped ->', os.path.basename(font), len(data), 'bytes')


if __name__ == '__main__':
    main(sys.argv[1])
